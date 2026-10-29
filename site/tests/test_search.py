import pytest
from fastapi.testclient import TestClient

from recipes_site import catalog, counts, search
from recipes_site.app import create_app
from recipes_site.config import Settings


def _terms(q: str) -> list[search.Term]:
    return search.parse(q).terms


SOUP = """# Soup

## Ingredients

- 1 leek
- 3 tablespoons heavy cream
- 2 potatoes
"""

STEW = """# Stew

## Ingredients

- 2 leeks, thinly sliced
- 1 [red sauce](../sauces/sauce-red.md)
"""

LOAF = """# Loaf

## Ingredients

- ½ cup sour cream
- 1 tablespoon creamy peanut butter
"""


def _cat() -> catalog.Catalog:
    recipes = {
        slug: catalog.parse_recipe(slug, text)
        for slug, text in (("x/soup", SOUP), ("x/stew", STEW), ("x/loaf", LOAF))
    }
    return catalog.Catalog(categories=[], recipes=recipes, house_notes="")


def _find(q: str) -> list[tuple[str, list[str]]]:
    return [(g.label, [h.recipe.title for h in g.hits]) for g in search.find(_cat(), _terms(q))]


def test_plurals_fold_both_ways() -> None:
    assert _find("leek") == [("Uses leek", ["Soup", "Stew"])]
    assert _find("leeks") == [("Uses leeks", ["Soup", "Stew"])]
    assert _find("potato") == [("Uses potato", ["Soup"])]


@pytest.mark.parametrize(
    ("typed", "written"),
    [("peach", "peaches"), ("cookie", "cookies"), ("berry", "berries"), ("creme", "crème")],
)
def test_fold_matches_the_other_spelling(typed: str, written: str) -> None:
    assert search.fold(typed) == search.fold(written)


def test_tags_and_cut_off_terms_are_not_ingredients() -> None:
    assert [t.text for t in _terms("leeks, #vegan")] == ["leeks"]
    long = "leeks, " + "x" * search.MAX_QUERY
    assert [t.text for t in _terms(long)] == ["leeks"]


def test_whole_words_only() -> None:
    # "cream" is in "sour cream" but not "creamy".
    assert _find("cream") == [("Uses cream", ["Loaf", "Soup"])]
    hit = search.find(_cat(), _terms("cream"))[0].hits[0]
    assert [str(line.html) for line in hit.lines] == ["sour <mark>cream</mark>"]


def test_several_terms_rank_by_how_many_they_use() -> None:
    assert _find("leeks, cream") == [("Uses both", ["Soup"]), ("Uses one", ["Loaf", "Stew"])]
    assert _find("leek, cream, potato")[0] == ("Uses all 3", ["Soup"])


def test_multi_word_terms_and_links() -> None:
    assert _find("heavy cream") == [("Uses heavy cream", ["Soup"])]
    assert _find("red sauce") == [("Uses red sauce", ["Stew"])]


def test_lines_keep_their_amount() -> None:
    hit = search.find(_cat(), _terms("leek"))[0].hits[1]
    assert (hit.lines[0].amount, str(hit.lines[0].html)) == (
        "2",
        "<mark>leeks</mark>, thinly sliced",
    )


@pytest.mark.parametrize("q", ["", "  ", "#tea", "a", ",,,"])
def test_no_terms(q: str) -> None:
    assert _terms(q) == []


def test_repeats_and_limits() -> None:
    assert [(t.text, t.parts) for t in _terms("leeks, cream, Leek")] == [
        ("leeks", (0, 2)),
        ("cream", (1,)),
    ]
    many = search.parse(", ".join(f"thing{i}" for i in "abcdefgh"))
    assert len(many.terms) == search.MAX_TERMS
    assert many.dropped
    assert not search.parse("leeks, cream").dropped


def test_overlapping_matches_highlight_whole() -> None:
    cat = catalog.Catalog(
        categories=[],
        recipes={
            "x/a": catalog.parse_recipe("x/a", "# A\n\n## Ingredients\n\n- 8 oz cream cheese\n")
        },
        house_notes="",
    )
    line = search.find(cat, _terms("cream, cream cheese"))[0].hits[0].lines[0]
    assert str(line.html) == "<mark>cream cheese</mark>"


def test_matches_are_escaped() -> None:
    cat = catalog.Catalog(
        categories=[],
        recipes={"x/a": catalog.parse_recipe("x/a", "# A\n\n## Ingredients\n\n- 1 <b>leek</b>\n")},
        house_notes="",
    )
    line = search.find(cat, _terms("leek"))[0].hits[0].lines[0]
    assert "<b>" not in str(line.html)


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(counts, "bump", lambda *_args, **_kw: None)
    return TestClient(create_app(Settings(auth_disabled=False, asset_version="abc1234")))


def test_endpoint_lists_real_recipes(client: TestClient) -> None:
    r = client.get("/search/ingredients", params={"q": "leeks, cream"})
    assert r.status_code == 200
    assert "Uses both" in r.text
    assert 'href="/entrees/soups-and-stews/soupe-dauphinoise"' in r.text
    assert 'data-drop-parts="1"' in r.text
    assert "1 recipe" in r.text or "recipes by ingredient" in r.text
    assert "set-cookie" not in r.headers


def test_endpoint_empty_query_clears_the_chips(client: TestClient) -> None:
    r = client.get("/search/ingredients", params={"q": ""})
    assert r.status_code == 200
    assert 'id="search-terms"' in r.text
    assert "<section" not in r.text


def test_index_has_the_search_wiring(client: TestClient) -> None:
    r = client.get("/")
    assert 'hx-get="/search/ingredients"' in r.text
    assert "data-ing-results" in r.text
