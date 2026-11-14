"""LeAnn's recipe box: a second catalog at /moms-recipe-box, kept apart from the main one."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from recipes_site import catalog, counts, toc
from recipes_site.app import create_app
from recipes_site.config import Settings

REPO = Path(__file__).resolve().parents[2]
BOX = REPO / catalog.BOX_DIR


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(counts, "bump", lambda *_args, **_kw: None)
    return TestClient(create_app(Settings(auth_disabled=False, asset_version="abc1234")))


def test_every_box_recipe_is_well_formed() -> None:
    assert catalog.check(BOX, box=True) == []


def test_box_fields_are_rejected_in_the_main_collection(tmp_path: Path) -> None:
    (tmp_path / "breakfast").mkdir()
    (tmp_path / "breakfast" / "oats.md").write_text("---\ncredit: Someone\n---\n\n# Oats\n")
    assert catalog.check(tmp_path) == ["breakfast/oats.md: unknown front matter field `credit`"]


def test_every_lives_on_points_at_a_main_recipe() -> None:
    main = catalog.load(REPO)
    missing = [
        f"{r.slug} -> {r.lives_on}"
        for r in catalog.load(BOX).recipes.values()
        if r.lives_on and r.lives_on not in main.recipes
    ]
    assert missing == []


def test_the_main_catalog_and_readme_list_skip_the_box() -> None:
    box_slugs = set(catalog.load(BOX).recipes)
    assert box_slugs
    assert not any(s.startswith(catalog.BOX_DIR) for s in catalog.load(REPO).recipes)
    assert catalog.BOX_DIR not in toc.render(catalog.load(REPO))


def test_miscellaneous_is_the_last_tab() -> None:
    assert catalog.load(BOX).categories[-1].title == "Miscellaneous"


def test_box_index_is_noindex(client: TestClient) -> None:
    r = client.get("/moms-recipe-box")
    assert r.status_code == 200
    assert r.headers["x-robots-tag"] == "noindex, nofollow"
    assert '<meta name="robots" content="noindex, nofollow">' in r.text
    assert "photos.app.goo.gl" in r.text
    # The box is its own world: no shopping-list button in its header.
    assert 'href="/list"' not in r.text


def test_box_recipe_page_renders_and_scales(client: TestClient) -> None:
    slug = next(iter(catalog.load(BOX).recipes))
    r = client.get(f"/moms-recipe-box/{slug}?scale=2")
    assert r.status_code == 200
    assert r.headers["x-robots-tag"] == "noindex, nofollow"
    assert f'data-recipe="moms-recipe-box/{slug}"' in r.text
    assert "data-add-to-list" not in r.text
    assert "data-owner" not in r.text


def test_lives_on_links_to_the_main_recipe(client: TestClient) -> None:
    box = catalog.load(BOX)
    recipe = next(r for r in box.recipes.values() if r.lives_on)
    r = client.get(f"/moms-recipe-box/{recipe.slug}")
    assert f'class="lives-on" href="/{recipe.lives_on}"' in r.text


def test_unknown_box_recipe_is_404(client: TestClient) -> None:
    assert client.get("/moms-recipe-box/cakes/not-a-card").status_code == 404


def test_main_index_does_not_list_the_box(client: TestClient) -> None:
    assert "/moms-recipe-box/" not in client.get("/").text


def test_main_menu_links_to_the_box(client: TestClient) -> None:
    assert '<a href="/moms-recipe-box">Mom' in client.get("/").text


def test_a_folded_card_redirects_to_its_new_home(client: TestClient) -> None:
    r = client.get("/moms-recipe-box/cakes/cream-cheese-icing", follow_redirects=False)
    assert r.status_code == 301
    assert r.headers["location"] == "/moms-recipe-box/cakes/carrot-cake"
