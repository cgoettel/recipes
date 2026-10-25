"""Run the parser over the real recipes, so a new recipe that breaks it fails CI."""

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
    assert recipe.title == "Dutch Baby"
    assert recipe.subtitle == "German Pancakes"
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
