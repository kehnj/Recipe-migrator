# Recipe-migrator

Turns a recipe from a TikTok video into a recipe in **AnyList**.

AnyList has no public API. It can import any web page that carries standard
[schema.org Recipe](https://schema.org/Recipe) data, the format most recipe sites use.
This tool does the conversion:

All you provide is the TikTok **share link**. You never copy text out of TikTok.

```
TikTok link ──► description + subtitles + video frames (on-screen text) + speech transcript
            ──► Claude reads all of it and extracts a clean recipe (ingredients, steps, times)
            ──► recipe page with schema.org data, published on GitHub Pages
            ──► AnyList "Import Recipe from Web"
```

## Everyday use (from your phone)

1. In TikTok, tap **Share → Copy link**.
2. Open a **new issue** in this repo and paste the link into the title. That's all.
   - The tool downloads the video and reads the description, the spoken audio and any
     recipe text shown on screen.
   - Optional backup: attach **screenshots** to the issue (for example, of the expanded
     description). They're read too.
3. About a minute later the bot comments on the issue with a link like
   `https://<you>.github.io/Recipe-migrator/recipes/garlic-butter-noodles.html`.
4. In AnyList, go to **Recipes → + → Import Recipe from Web**. Paste that link and tap **Import**.

The comment also includes a plain-text version you can paste into AnyList by hand.

You can also run it from the **Actions** tab: **Import TikTok recipe → Run workflow**, then paste the URL.

## One-time setup

1. **API key:** in the repo, go to Settings → Secrets and variables → Actions → **New repository secret**.
   Name it `ANTHROPIC_API_KEY` and paste your key from console.anthropic.com.
2. **GitHub Pages:** go to Settings → Pages → *Deploy from a branch* and choose your default branch, folder `/docs`.
   - Pages on a **private** repo needs a paid GitHub plan. Pages sites are public, so anyone
     with a link can open it (the URLs aren't listed or advertised anywhere).
3. **Workflow permissions:** go to Settings → Actions → General → Workflow permissions and select
   **Read and write**.
4. Merge this code into the default branch. Issue-triggered workflows only run from the default branch.

Only the repo owner's issues trigger an import, so other people can't spend your API credits.

## Running locally

```bash
pip install ".[transcribe]"        # or plain "." to skip audio transcription
export ANTHROPIC_API_KEY=...
recipe-migrator "https://www.tiktok.com/@creator/video/123" --transcribe
```

This prints the recipe as text, so you can paste it into AnyList. It also writes
`docs/recipes/<name>.html`. Useful flags:

- `--image shot.png` (repeatable): also read screenshots
- `--notes "..."` / `--notes-file f.txt`: optional extra text
- `--base-url https://you.github.io/Recipe-migrator`: print the public import link
- `--transcribe`: transcribe the spoken audio with Whisper, for videos where the recipe is only spoken
- `--no-frames`: skip reading on-screen text from video frames (frames need `ffmpeg`)

## Limitations

- **TikTok sometimes blocks automated downloads.** The tool then falls back to TikTok's public
  oEmbed endpoint, which still returns the description, but without the video it can't read on-screen
  text or speech. If that happens, attach screenshots to a new issue.
- Up to 16 frames are sampled per video. On-screen text that flashes by very briefly can be missed.
- When the creator gives no quantities, they're left out rather than guessed. If anything had to be
  estimated, the page shows a warning.

## Development

```bash
pip install -e ".[dev]" && pytest
```
