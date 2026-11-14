import json
import re

from recipe_migrator import cli, render, tiktok
from recipe_migrator.extract import IngredientSection, Recipe


def sample():
    return Recipe(
        found_recipe=True, name="Garlic Butter Noodles </script>", description="Quick noodles.",
        servings="2 servings", prep_time_minutes=5, cook_time_minutes=10,
        ingredient_sections=[
            IngredientSection(heading="", items=["8 oz spaghetti", "4 cloves garlic"]),
            IngredientSection(heading="Sauce", items=["2 tbsp butter", "1 tbsp soy sauce"]),
        ],
        steps=["Boil noodles.", "Melt butter with garlic.", "Toss."],
        notes="Add chili crisp.", inferred=False,
    )


def test_json_ld_is_valid_schema_recipe():
    page = render.to_html(sample(), "https://www.tiktok.com/@a/video/1", "chef", "https://img")
    block = re.search(r'<script type="application/ld\+json">(.*?)</script>', page, re.S).group(1)
    data = json.loads(block)
    assert data["@type"] == "Recipe"
    assert data["recipeIngredient"] == ["8 oz spaghetti", "4 cloves garlic", "2 tbsp butter", "1 tbsp soy sauce"]
    assert len(data["recipeInstructions"]) == 3
    assert data["totalTime"] == "PT15M"
    assert data["name"].endswith("</script>")  # escaping round-trips


def test_text_has_sections():
    text = render.to_text(sample(), "u")
    assert "INGREDIENTS\n8 oz spaghetti" in text and "Sauce:" in text and "STEPS\nBoil noodles." in text


def test_vtt_parsing_dedupes():
    vtt = "WEBVTT\n\n1\n00:00.000 --> 00:01.000\nAdd <b>salt</b>\n\n2\n00:01.000 --> 00:02.000\nAdd salt\n"
    assert tiktok._vtt_to_text(vtt) == "Add salt"


def test_cli_end_to_end(tmp_path, monkeypatch):
    monkeypatch.setattr(cli.tiktok, "fetch", lambda url, transcribe=False: tiktok.TikTokPost(url=url, caption="noodles!", author="chef"))
    monkeypatch.setattr(cli, "extract_recipe", lambda src, notes: sample())
    out = tmp_path / "r.json"
    rc = cli.main(["https://www.tiktok.com/@a/video/1", "--site-dir", str(tmp_path / "docs"),
                   "--base-url", "https://me.github.io/repo", "--json-out", str(out)])
    assert rc == 0
    r = json.loads(out.read_text())
    assert r["public_url"] == "https://me.github.io/repo/recipes/garlic-butter-noodles-script.html"
    assert "garlic-butter-noodles" in (tmp_path / "docs" / "index.html").read_text()
