import pytest
from fastapi.testclient import TestClient

from recipes_site import counts
from recipes_site.app import create_app
from recipes_site.config import Settings


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    # No database in these tests: counting is best effort and must not break pages.
    monkeypatch.setattr(counts, "bump", lambda *_args, **_kw: None)
    return TestClient(create_app(Settings(auth_disabled=False, asset_version="abc1234")))


def test_health_reports_build(client: TestClient) -> None:
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["build"] == "abc1234"


def test_index_lists_recipes(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200
    assert "Dutch Baby" in r.text
    assert 'href="/breakfast/pancake-dutch-baby"' in r.text


def test_recipe_page(client: TestClient) -> None:
    r = client.get("/breakfast/pancake-dutch-baby")
    assert r.status_code == 200
    assert "4 tablespoons" in r.text
    assert 'data-recipe="breakfast/pancake-dutch-baby"' in r.text


def test_recipe_scales(client: TestClient) -> None:
    r = client.get("/breakfast/pancake-dutch-baby?scale=2")
    assert "1 stick (8 tablespoons)" in r.text  # ½ stick butter, doubled
    assert "Times don’t scale" in r.text


def test_md_suffix_works(client: TestClient) -> None:
    assert client.get("/breakfast/pancake-dutch-baby.md").status_code == 200


def test_unknown_recipe_404s(client: TestClient) -> None:
    r = client.get("/nope/not-a-recipe")
    assert r.status_code == 404
    assert "Not here" in r.text


def test_metrics_hidden_from_the_public(client: TestClient) -> None:
    assert client.get("/metrics").status_code == 200
    assert client.get("/metrics", headers={"CF-Ray": "abc"}).status_code == 404


def test_links_render_outside_the_check_buttons() -> None:
    from recipes_site import app as app_module

    html, links = app_module.split_links('Make <a href="/x/y">red sauce</a> first')
    assert "<a" not in html
    assert links == [("/x/y", "red sauce")]


def test_private_paths_closed_without_access_config(client: TestClient) -> None:
    assert client.get("/me").status_code == 403


def test_every_recipe_renders(client: TestClient) -> None:
    from recipes_site import catalog
    from recipes_site.config import get_settings

    cat = catalog.load(get_settings().content_dir)
    for slug in cat.recipes:
        assert client.get(f"/{slug}").status_code == 200, slug
