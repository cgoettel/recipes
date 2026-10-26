from fractions import Fraction
from pathlib import Path

from fastapi.testclient import TestClient

from recipes_site import catalog, counts, shopping
from recipes_site.app import create_app
from recipes_site.config import Settings

A = """# A

## Ingredients

- 1 onion, diced
- 2 cups flour
- 1 tablespoon butter
- Salt to taste
- 1 cup warm water
"""

B = """# B

## Ingredients

- 2 onions
- 1 cup flour
- 2 lb ground beef
- 3 cloves garlic
"""


STAPLES = catalog.parse_staples(
    (Path(__file__).resolve().parents[2] / catalog.STAPLES_FILE).read_text(encoding="utf-8")
)


def _sections(scale_a: Fraction = Fraction(1)) -> dict[str, dict[str, str]]:
    a = catalog.parse_recipe("x/a", A)
    b = catalog.parse_recipe("x/b", B)
    built = shopping.build([(a, scale_a), (b, Fraction(1))], STAPLES)
    return {s.name: {e.key: e.amount for e in s.entries} for s in built}


def test_merges_duplicates_and_sums() -> None:
    s = _sections()
    assert s["Produce"]["onion"] == "3"
    assert s["Staples"]["flour"] == "3 cups"
    assert s["Meat and fish"]["ground beef"] == "2 lb"
    assert s["Produce"]["garlic"] == "3 cloves"


def test_scale_applies_per_recipe() -> None:
    assert _sections(Fraction(2))["Staples"]["flour"] == "5 cups"


def test_water_is_never_listed_and_staples_collapse() -> None:
    s = _sections()
    assert all("water" not in keys for keys in s.values())
    assert "salt" in s["Staples"] and "butter" in s["Staples"]


def test_canned_goes_to_pantry() -> None:
    assert shopping.section_for("crushed tomato", {"can"}) == "Pantry"
    assert shopping.section_for("tomato", {None}) == "Produce"


def test_sections_match_whole_words() -> None:
    assert shopping.section_for("eggplant") == "Produce"
    assert shopping.section_for("peanut butter") == "Pantry"
    assert shopping.section_for("graham cracker") == "Pantry"
    assert shopping.section_for("rolled oat") == "Pantry"
    assert shopping.section_for("apple cider vinegar") == "Pantry"


def test_linked_ingredient_label() -> None:
    recipe = catalog.parse_recipe(
        "x/y", "# Y\n\n## Ingredients\n\n- 1 cup [red sauce](../sauces/sauce-red.md)\n"
    )
    entry = shopping.build([(recipe, Fraction(1))])[0].entries[0]
    assert entry.label == "red sauce"


def test_normalize() -> None:
    assert shopping.normalize("large tomatoes, diced") == "tomato"
    assert shopping.normalize("fresh cilantro (a handful)") == "cilantro"


def test_plan_param() -> None:
    assert shopping.parse_plan(["a/b@2", "c/d"]) == [("a/b", Fraction(2)), ("c/d", Fraction(1))]


def test_list_page(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(counts, "bump", lambda *_a, **_k: None)
    client = TestClient(create_app(Settings()))
    empty = client.get("/list")
    assert "Nothing here yet" in empty.text
    r = client.get("/list?r=breakfast/pancake-dutch-baby@2&r=bread/bread-french@1")
    assert r.status_code == 200
    assert "Dairy and eggs" in r.text
    assert "6" in r.text  # eggs, doubled
    # The service worker is gone; app.js unregisters it where it was installed.
    assert client.get("/sw.js").status_code == 404


def test_staples_come_from_the_markdown_file() -> None:
    assert {"salt", "flour", "butter", "vanilla extract"} <= STAPLES
    assert not any(s.startswith("#") for s in STAPLES)
    # The catalog reads the same file, and it isn't a recipe.
    cat = catalog.load(Path(__file__).resolve().parents[2])
    assert cat.staples == STAPLES
    assert catalog.STAPLES_FILE.removesuffix(".md") not in cat.recipes


def test_staples_match_plurals() -> None:
    bay = catalog.parse_recipe("x/c", "# C\n\n## Ingredients\n\n- 2 bay leaves\n")
    built = shopping.build([(bay, Fraction(1))], frozenset({"bay leaves"}))
    assert [s.name for s in built] == ["Staples"]
