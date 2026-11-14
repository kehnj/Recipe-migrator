"""Pull everything useful out of a TikTok post from just its link: the
description, subtitles, still frames (for on-screen text) and, optionally, a
transcript of the spoken audio. Nobody has to copy text out of the app."""

from __future__ import annotations

import base64
import json
import re
import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

MAX_FRAMES = 16


@dataclass
class TikTokPost:
    url: str
    title: str = ""
    caption: str = ""
    author: str = ""
    thumbnail: str = ""
    subtitles: str = ""
    transcript: str = ""
    frames: list[bytes] = field(default_factory=list)  # JPEG stills from the video
    warnings: list[str] = field(default_factory=list)

    def has_content(self) -> bool:
        return bool(self.caption or self.subtitles or self.transcript or self.frames)

    def source_text(self) -> str:
        """All the text we found, labelled, for the extraction model."""
        parts = [f"TikTok URL: {self.url}"]
        if self.author:
            parts.append(f"Creator: {self.author}")
        if self.title and self.title != self.caption:
            parts.append(f"Title:\n{self.title}")
        if self.caption:
            parts.append(f"Caption / description:\n{self.caption}")
        if self.subtitles:
            parts.append(f"On-video captions (subtitles):\n{self.subtitles}")
        if self.transcript:
            parts.append(f"Transcript of spoken audio:\n{self.transcript}")
        if self.frames:
            parts.append(
                f"{len(self.frames)} still frames from the video are attached, in order; "
                "read any recipe text shown on screen."
            )
        return "\n\n".join(parts)


def _vtt_to_text(vtt: str) -> str:
    lines: list[str] = []
    for line in vtt.splitlines():
        line = line.strip()
        if not line or line == "WEBVTT" or "-->" in line or line.isdigit():
            continue
        if line.startswith(("NOTE", "Kind:", "Language:")):
            continue
        line = re.sub(r"<[^>]+>", "", line)
        if not lines or lines[-1] != line:  # auto-captions repeat lines
            lines.append(line)
    return "\n".join(lines)


def _oembed(url: str) -> dict:
    """TikTok's public oEmbed endpoint: no login, returns the caption as `title`."""
    endpoint = "https://www.tiktok.com/oembed?url=" + urllib.parse.quote(url, safe="")
    req = urllib.request.Request(endpoint, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.load(resp)


def extract_frames(video: Path, duration: float | None, out_dir: Path) -> list[bytes]:
    """Evenly spaced, downscaled JPEG stills so on-screen text can be read."""
    if not shutil.which("ffmpeg"):
        return []
    duration = duration or 60.0
    fps = min(1.0, MAX_FRAMES / max(duration, 1.0))
    subprocess.run(
        [
            "ffmpeg", "-loglevel", "error", "-i", str(video),
            "-vf", f"fps={fps:.4f},scale=768:-2", "-q:v", "4",
            str(out_dir / "frame_%03d.jpg"),
        ],
        check=True,
    )
    frames = sorted(out_dir.glob("frame_*.jpg"))
    if len(frames) > MAX_FRAMES:
        step = len(frames) / MAX_FRAMES
        frames = [frames[int(i * step)] for i in range(MAX_FRAMES)]
    return [f.read_bytes() for f in frames]


def _transcribe(media: Path) -> str:
    from faster_whisper import WhisperModel  # optional dependency

    model = WhisperModel("small", device="cpu", compute_type="int8")
    segments, _ = model.transcribe(str(media))
    return " ".join(s.text.strip() for s in segments)


def fetch(url: str, transcribe: bool = False, frames: bool = True) -> TikTokPost:
    post = TikTokPost(url=url)

    try:
        import yt_dlp

        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            download = frames or transcribe
            opts = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": not download,
                "format": "best[height<=720]/best",
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitlesformat": "vtt",
                "outtmpl": f"{tmp}/post.%(ext)s",
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)

            post.title = info.get("title") or ""
            post.caption = info.get("description") or ""
            post.author = info.get("uploader") or info.get("creator") or ""
            post.thumbnail = info.get("thumbnail") or ""

            vtts = sorted(tmpdir.glob("*.vtt"))
            vtts.sort(key=lambda p: (".en" not in p.name and ".eng" not in p.name, p.name))
            if vtts:
                post.subtitles = _vtt_to_text(vtts[0].read_text(errors="ignore"))

            media = [p for p in tmpdir.iterdir() if p.suffix not in (".vtt", ".json", ".jpg")]
            if media and frames:
                frame_dir = tmpdir / "frames"
                frame_dir.mkdir()
                try:
                    post.frames = extract_frames(media[0], info.get("duration"), frame_dir)
                except Exception as exc:  # noqa: BLE001
                    post.warnings.append(f"Couldn't grab video frames ({exc}).")
            if media and transcribe:
                try:
                    post.transcript = _transcribe(media[0])
                except ImportError:
                    post.warnings.append(
                        "Transcription skipped: install with `pip install .[transcribe]`."
                    )
    except Exception as exc:  # noqa: BLE001 - fall back to oEmbed below
        post.warnings.append(f"yt-dlp could not read the post ({exc}); trying oEmbed.")

    if not post.caption:
        try:
            data = _oembed(url)
            post.caption = data.get("title") or ""
            post.author = post.author or data.get("author_name") or ""
            post.thumbnail = post.thumbnail or data.get("thumbnail_url") or ""
        except Exception as exc:  # noqa: BLE001
            post.warnings.append(f"oEmbed lookup failed ({exc}).")

    return post


def image_block(data: bytes, media_type: str = "image/jpeg") -> dict:
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": media_type, "data": base64.b64encode(data).decode()},
    }
