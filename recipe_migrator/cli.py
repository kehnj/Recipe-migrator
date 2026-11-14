"""Command line entry point.

    recipe-migrator https://www.tiktok.com/@someone/video/123 [--notes "pasted caption"]
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

from . import render, tiktok
from .extract import extract_recipe


def rebuild_index(site_dir: Path) -> None:
    recipes_dir = site_dir / "recipes"
    pages = sorted(recipes_dir.glob("*.html"), key=lambda p: p.stat().st_mtime, reverse=True)
    entries = []
    for page in pages:
        m = re.search(r"<title>(.*?)</title>", page.read_text(encoding="utf-8"), re.S)
        title = html.unescape(m.group(1)) if m else page.stem
        entries.append((title, f"recipes/{page.name}"))
    (site_dir / "index.html").write_text(render.index_html(entries), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Convert a TikTok recipe for AnyList import.")
    p.add_argument("url", help="TikTok video URL (share link is fine)")
    p.add_argument("--notes", default="", help="Extra text, e.g. a caption you copied by hand")
    p.add_argument("--notes-file", type=Path, help="Read extra text from a file")
    p.add_argument("--transcribe", action="store_true", help="Transcribe the audio (needs .[transcribe])")
    p.add_argument("--site-dir", type=Path, default=Path("docs"), help="Where to write the HTML page")
    p.add_argument("--base-url", default="", help="Public URL of --site-dir, e.g. GitHub Pages URL")
    p.add_argument("--json-out", type=Path, help="Write a machine-readable result summary here")
    args = p.parse_args(argv)

    notes = args.notes
    if args.notes_file and args.notes_file.exists():
        notes = (notes + "\n" + args.notes_file.read_text(encoding="utf-8")).strip()

    print(f"Fetching {args.url} ...", file=sys.stderr)
    post = tiktok.fetch(args.url, transcribe=args.transcribe)
    for w in post.warnings:
        print(f"warning: {w}", file=sys.stderr)
    if not (post.caption or post.subtitles or post.transcript or notes):
        print("error: couldn't read any text from that post. Paste the caption with --notes.", file=sys.stderr)
        return 2

    print("Extracting recipe with Claude ...", file=sys.stderr)
    recipe = extract_recipe(post.source_text(), notes)
    if not recipe.found_recipe:
        print("error: no recipe found in the post text. Try --transcribe or --notes.", file=sys.stderr)
        return 3

    slug = render.slugify(recipe.name)
    recipes_dir = args.site_dir / "recipes"
    recipes_dir.mkdir(parents=True, exist_ok=True)
    page = recipes_dir / f"{slug}.html"
    page.write_text(render.to_html(recipe, args.url, post.author, post.thumbnail), encoding="utf-8")
    rebuild_index(args.site_dir)

    public_url = f"{args.base_url.rstrip('/')}/recipes/{page.name}" if args.base_url else ""
    text = render.to_text(recipe, args.url)

    print(text)
    print(f"\nSaved {page}", file=sys.stderr)
    if public_url:
        print(f"Import into AnyList from: {public_url}", file=sys.stderr)

    if args.json_out:
        args.json_out.write_text(
            json.dumps(
                {
                    "name": recipe.name,
                    "page": str(page),
                    "public_url": public_url,
                    "text": text,
                    "inferred": recipe.inferred,
                    "warnings": post.warnings,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
