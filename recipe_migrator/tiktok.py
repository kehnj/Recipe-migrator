"""Pull everything useful out of a TikTok post: caption, captions/subtitles, and
(optionally) a transcript of the spoken audio."""

from __future__ import annotations

import json
import re
import tempfile
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TikTokPost:
    url: str
    title: str = ""
    caption: str = ""
    author: str = ""
    thumbnail: str = ""
    subtitles: str = ""
    transcript: str = ""
    warnings: list[str] = field(default_factory=list)

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


def _transcribe(audio_path: Path) -> str:
    from faster_whisper import WhisperModel  # optional dependency

    model = WhisperModel("small", device="cpu", compute_type="int8")
    segments, _ = model.transcribe(str(audio_path))
    return " ".join(s.text.strip() for s in segments)


def fetch(url: str, transcribe: bool = False) -> TikTokPost:
    post = TikTokPost(url=url)

    try:
        import yt_dlp

        with tempfile.TemporaryDirectory() as tmp:
            opts = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": not transcribe,
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitlesformat": "vtt",
                "outtmpl": f"{tmp}/post.%(ext)s",
            }
            if transcribe:
                opts["format"] = "bestaudio/best"
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)

            post.title = info.get("title") or ""
            post.caption = info.get("description") or ""
            post.author = info.get("uploader") or info.get("creator") or ""
            post.thumbnail = info.get("thumbnail") or ""

            vtts = sorted(Path(tmp).glob("*.vtt"))
            # Prefer English subtitle tracks when several exist.
            vtts.sort(key=lambda p: (".en" not in p.name and ".eng" not in p.name, p.name))
            if vtts:
                post.subtitles = _vtt_to_text(vtts[0].read_text(errors="ignore"))

            if transcribe:
                media = [p for p in Path(tmp).iterdir() if p.suffix not in (".vtt", ".json")]
                if media:
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
