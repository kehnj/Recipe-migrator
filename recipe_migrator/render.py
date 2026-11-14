"""Render a recipe as (1) an HTML page with schema.org Recipe JSON-LD, which
AnyList's "Import from Web" understands, and (2) plain text for pasting."""

from __future__ import annotations

import html
import json
import re
from datetime import date

from .extract import Recipe


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:60] or "recipe"


def _iso_minutes(minutes: int | None) -> str | None:
    return f"PT{minutes}M" if minutes else None


def all_ingredients(recipe: Recipe) -> list[str]:
    return [item for s in recipe.ingredient_sections for item in s.items]


def json_ld(recipe: Recipe, source_url: str, author: str = "", image: str = "") -> dict:
    data: dict = {
        "@context": "https://schema.org",
        "@type": "Recipe",
        "name": recipe.name,
        "description": recipe.description,
        "recipeIngredient": all_ingredients(recipe),
        "recipeInstructions": [{"@type": "HowToStep", "text": s} for s in recipe.steps],
        "url": source_url,
        "isBasedOn": source_url,
        "datePublished": date.today().isoformat(),
    }
    if recipe.servings:
        data["recipeYield"] = recipe.servings
    if author:
        data["author"] = {"@type": "Person", "name": author}
    if image:
        data["image"] = [image]
    for key, minutes in (
        ("prepTime", recipe.prep_time_minutes),
        ("cookTime", recipe.cook_time_minutes),
    ):
        if iso := _iso_minutes(minutes):
            data[key] = iso
    total = (recipe.prep_time_minutes or 0) + (recipe.cook_time_minutes or 0)
    if total:
        data["totalTime"] = _iso_minutes(total)
    return data


def to_text(recipe: Recipe, source_url: str) -> str:
    """Plain text laid out the way AnyList's recipe editor expects pasted lines."""
    out = [recipe.name, ""]
    if recipe.servings:
        out.append(f"Servings: {recipe.servings}")
    if recipe.prep_time_minutes:
        out.append(f"Prep: {recipe.prep_time_minutes} min")
    if recipe.cook_time_minutes:
        out.append(f"Cook: {recipe.cook_time_minutes} min")
    out += ["", "INGREDIENTS"]
    for section in recipe.ingredient_sections:
        if section.heading:
            out.append(f"{section.heading}:")
        out += section.items
    out += ["", "STEPS"]
    out += recipe.steps
    if recipe.notes:
        out += ["", "NOTES", recipe.notes]
    out += ["", f"Source: {source_url}"]
    return "\n".join(out)


def to_html(recipe: Recipe, source_url: str, author: str = "", image: str = "") -> str:
    e = html.escape
    ld = json.dumps(json_ld(recipe, source_url, author, image), indent=2, ensure_ascii=False)
    ld = ld.replace("</", "<\\/")  # keep the script tag intact

    sections = []
    for s in recipe.ingredient_sections:
        heading = f"<h3>{e(s.heading)}</h3>" if s.heading else ""
        items = "".join(f"<li>{e(i)}</li>" for i in s.items)
        sections.append(f"{heading}<ul>{items}</ul>")
    steps = "".join(f"<li>{e(s)}</li>" for s in recipe.steps)
    meta = " · ".join(
        x
        for x in (
            e(recipe.servings),
            f"Prep {recipe.prep_time_minutes} min" if recipe.prep_time_minutes else "",
            f"Cook {recipe.cook_time_minutes} min" if recipe.cook_time_minutes else "",
        )
        if x
    )
    byline = f" by {e(author)}" if author else ""
    notes = f"<h2>Notes</h2><p>{e(recipe.notes)}</p>" if recipe.notes else ""
    inferred = (
        '<p class="warn">Some quantities or steps were estimated — check the video.</p>'
        if recipe.inferred
        else ""
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(recipe.name)}</title>
<meta name="description" content="{e(recipe.description)}">
<script type="application/ld+json">
{ld}
</script>
<style>
  body {{ font: 17px/1.5 system-ui, sans-serif; max-width: 680px; margin: 0 auto; padding: 16px; color: #222; background: #fff; }}
  h1 {{ margin-bottom: 4px; }} .meta, .src {{ color: #666; }} .warn {{ color: #a15c00; }}
  li {{ margin: 4px 0; }}
  @media (prefers-color-scheme: dark) {{ body {{ color: #eee; background: #161616; }} .meta, .src {{ color: #aaa; }} }}
</style>
</head>
<body>
<h1>{e(recipe.name)}</h1>
<p class="meta">{meta}</p>
<p>{e(recipe.description)}</p>
{inferred}
<h2>Ingredients</h2>
{''.join(sections)}
<h2>Steps</h2>
<ol>{steps}</ol>
{notes}
<p class="src">From <a href="{e(source_url)}">TikTok</a>{byline}.</p>
</body>
</html>
"""


def index_html(entries: list[tuple[str, str]]) -> str:
    """entries: (title, relative href), newest first."""
    items = "".join(
        f'<li><a href="{html.escape(href)}">{html.escape(title)}</a></li>' for title, href in entries
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Imported Recipes</title>
<style>body {{ font: 17px/1.5 system-ui, sans-serif; max-width: 680px; margin: 0 auto; padding: 16px; }}</style>
</head><body><h1>Imported recipes</h1><ul>{items}</ul></body></html>
"""
