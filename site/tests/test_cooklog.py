import datetime as dt

import pytest
from fastapi.testclient import TestClient

from recipes_site import cooklog, counts
from recipes_site.app import create_app
from recipes_site.config import Settings


@pytest.fixture
def logged(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str | None, dt.date | None]]:
    calls: list[tuple[str, str | None, dt.date | None]] = []
    monkeypatch.setattr(counts, "bump", lambda *_a, **_k: None)
    monkeypatch.setattr(counts, "top", lambda *_a, **_k: [("breakfast/pancake-dutch-baby", 3)])
    monkeypatch.setattr(
        cooklog, "add", lambda slug, note, made_on=None: calls.append((slug, note, made_on))
    )
    monkeypatch.setattr(
        cooklog, "status", lambda _slug: cooklog.Status(count=2, last=dt.date(2026, 10, 1))
    )
    monkeypatch.setattr(
        cooklog,
        "recent",
        lambda *_a, **_k: [
            cooklog.Made("breakfast/pancake-dutch-baby", dt.date(2026, 10, 1), "great")
        ],
    )
    monkeypatch.setattr(cooklog, "made_slugs", lambda: {"breakfast/pancake-dutch-baby"})
    return calls


def _client(auth_disabled: bool) -> TestClient:
    return TestClient(create_app(Settings(auth_disabled=auth_disabled)), follow_redirects=False)


def test_private_pages_need_access(logged: list[object]) -> None:  # noqa: ARG001
    client = _client(auth_disabled=False)
    assert client.get("/me").status_code == 403
    assert client.get("/me/status?slug=x").status_code == 403
    assert client.post("/me/log", data={"slug": "x"}).status_code == 403


def test_owner_pages(logged: list[object]) -> None:  # noqa: ARG001
    client = _client(auth_disabled=True)
    page = client.get("/me")
    assert "Cook log" in page.text and "“great”" in page.text and "Untested" in page.text
    assert client.get("/me/status?slug=x").json() == {"count": 2, "last": "2026-10-01"}


def test_log_requires_same_origin(logged: list[tuple[str, str | None, dt.date | None]]) -> None:
    client = _client(auth_disabled=True)
    form = {"slug": "breakfast/pancake-dutch-baby", "note": "more nutmeg", "made_on": "2026-10-24"}
    assert (
        client.post("/me/log", data=form, headers={"Origin": "https://evil.example"}).status_code
        == 403
    )
    r = client.post("/me/log", data=form, headers={"Origin": "http://testserver"})
    assert r.status_code == 303
    assert logged == [("breakfast/pancake-dutch-baby", "more nutmeg", dt.date(2026, 10, 24))]


def test_unknown_recipe_not_logged(logged: list[object]) -> None:  # noqa: ARG001
    client = _client(auth_disabled=True)
    r = client.post("/me/log", data={"slug": "nope/nope"}, headers={"Origin": "http://testserver"})
    assert r.status_code == 404


def test_recipe_page_has_hidden_owner_widget(logged: list[object]) -> None:  # noqa: ARG001
    html = _client(auth_disabled=False).get("/breakfast/pancake-dutch-baby").text
    assert 'data-owner data-slug="breakfast/pancake-dutch-baby" hidden' in html
