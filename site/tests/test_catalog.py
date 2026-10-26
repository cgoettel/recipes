"""Run the parser over the real recipes, so a new recipe that breaks it fails CI."""

from pathlib import Path

from recipes_site import catalog
from recipes_site.config import get_settings


def _catalog() -> catalog.Catalog:
    return catalog.load(get_settings().content_dir)


def test_every_readme_link_loads() -> None:
    cat = _catalog()
    entries = [e for c in cat.categories for s in c.subcategories for e in s.entries]
    assert len(entries) > 150
    assert {e.slug for e in entries} == set(cat.recipes)


def test_dutch_baby_parses() -> None:
    recipe = _catalog().recipes["breakfast/pancake-dutch-baby"]
    assert recipe.title == "Dutch baby"
    assert recipe.subtitle == "German pancakes"
    assert recipe.family == "Pancakes"
    assert recipe.tag == "breakfast"
    assert len(recipe.ingredient_groups[0].items) == 7
    assert len(recipe.step_groups[0].items) == 5


def test_most_recipes_are_structured() -> None:
    recipes = list(_catalog().recipes.values())
    structured = [r for r in recipes if r.structured]
    assert len(structured) / len(recipes) > 0.85


def test_links_point_at_site_pages() -> None:
    text = "See [red sauce](../../sauces-and-condiments/sauces/sauce-red.md)."
    out = catalog.rewrite_links(text, "entrees/italian")
    assert "](/sauces-and-condiments/sauces/sauce-red)" in out


def test_split_title() -> None:
    recipe = catalog.parse_recipe("x/y", "# Plain Title\n")
    assert (recipe.title, recipe.subtitle) == ("Plain Title", None)


def test_every_recipe_file_is_well_formed() -> None:
    from pathlib import Path

    assert catalog.check(Path(__file__).resolve().parents[2]) == []


def test_check_catches_silent_mistakes(tmp_path) -> None:  # type: ignore[no-untyped-def]
    (tmp_path / "bread").mkdir()
    (tmp_path / "bread" / "a.md").write_text("---\nfamily: Bread\ntags: grill\n---\n\n# A\n")
    (tmp_path / "bread" / "b.md").write_text(
        "---\nfamily: Bread\nvariant: No\ntags: [grilled]\n---\n\n# B\n"
    )
    (tmp_path / "stray.md").write_text("# Stray\n")
    problems = "\n".join(catalog.check(tmp_path))
    assert "bread/a.md: `family` and `variant` go together" in problems
    assert "bread/a.md: `tags` should be a list" in problems
    assert "bread/b.md: `variant` should be text" in problems
    assert "tag `grilled` isn't in catalog.TAGS" in problems
    assert "stray.md: recipes live one or two folders deep" in problems


def test_check_flags_shorthand_units(tmp_path: Path) -> None:
    (tmp_path / "breakfast").mkdir()
    (tmp_path / "breakfast" / "oats.md").write_text(
        "# Oats\n\n## Ingredients\n\n- 1 C oats\n- 2 cups water\n\n## Instructions\n\n1. Cook.\n",
        encoding="utf-8",
    )
    assert catalog.check(tmp_path) == ["breakfast/oats.md: write `cup`, not `C`, in “1 C oats”"]
