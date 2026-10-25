from fractions import Fraction

from fastapi.testclient import TestClient

from recipes_site import bakers, catalog, counts
from recipes_site import ingredients as ing
from recipes_site.app import create_app
from recipes_site.config import Settings

DOUGH = """# Test Loaf

## Ingredients

- 4 cups (≈480 g) bread flour
- 1½ cups (≈340 g) water
- 2 teaspoons (≈12 g) salt
- 2 teaspoons (≈6 g) yeast

## Instructions

1. Mix.
"""


def test_gram_note_parses_and_scales() -> None:
    parsed = ing.parse("2 cups (≈240 g) flour")
    assert parsed.grams_low == 240
    assert parsed.grams_estimated
    assert parsed.item == "flour"
    assert ing.display(parsed, Fraction(2)).amount == "4 cups (≈480 g)"


def test_range_gram_note() -> None:
    parsed = ing.parse("5–5½ cups (≈600–660 g) flour")
    assert parsed.grams_low == Fraction(600)
    assert parsed.grams_high == Fraction(660)


def test_breakdown_ratios() -> None:
    b = bakers.breakdown(catalog.parse_recipe("bread/test", DOUGH))
    assert b is not None
    assert b.flour == 480
    ratios = {r.key: r.percent for r in b.ratios}
    assert round(float(ratios["hydration"])) == 71
    assert round(float(ratios["salt"]), 1) == 2.5
    assert "lean range" in next(r.note for r in b.ratios if r.key == "hydration")


def test_no_breakdown_without_weights() -> None:
    recipe = catalog.parse_recipe("x/y", "# X\n\n## Ingredients\n\n- 2 cups flour\n- 1 cup water\n")
    assert bakers.breakdown(recipe) is None


def test_dough_scale_is_clamped() -> None:
    assert bakers.dough_scale("838", Fraction(838)) == 1
    assert bakers.dough_scale("100000", Fraction(838)) == 4
    assert bakers.dough_scale("abc", Fraction(838)) is None


def test_bread_pages_show_the_view(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(counts, "bump", lambda *_a, **_k: None)
    client = TestClient(create_app(Settings()))
    r = client.get("/bread/bread-french")
    assert "Baker’s percentages" in r.text
    r = client.get("/bread/bread-french?dough=500")
    assert 'value="500"' in r.text
    assert client.get("/learn/bakers-percentages").status_code == 200
