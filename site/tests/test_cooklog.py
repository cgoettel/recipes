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
    assert client.get("/me/status?slug=x").text.strip() == "Made 2 times, last on 2026-10-01"


CSRF = {"Cookie": "recipes_csrf=tok", "X-CSRF-Token": "tok"}


def test_log_requires_the_csrf_token(logged: list[tuple[str, str | None, dt.date | None]]) -> None:
    client = _client(auth_disabled=True)
    form = {"slug": "breakfast/pancake-dutch-baby", "note": "more nutmeg", "made_on": "2026-10-24"}
    assert client.post("/me/log", data=form).status_code == 403
    wrong = {"Cookie": "recipes_csrf=tok", "X-CSRF-Token": "other"}
    assert client.post("/me/log", data=form, headers=wrong).status_code == 403
    assert logged == []
    r = client.post("/me/log", data=form, headers=CSRF)
    assert r.status_code == 200
    assert logged == [("breakfast/pancake-dutch-baby", "more nutmeg", dt.date(2026, 10, 24))]


def test_log_returns_the_new_status_line(logged: list[object]) -> None:  # noqa: ARG001
    client = _client(auth_disabled=True)
    r = client.post("/me/log", data={"slug": "breakfast/pancake-dutch-baby"}, headers=CSRF)
    assert r.text.strip() == "Made 2 times, last on 2026-10-01"


def test_public_posts_skip_the_csrf_check(logged: list[object]) -> None:  # noqa: ARG001
    # No public POST route exists yet; a 405 (not a CSRF 403) shows the check let it through.
    assert _client(auth_disabled=True).post("/breakfast/granola").status_code == 405


def test_csrf_cookie_only_on_private_pages(logged: list[object]) -> None:  # noqa: ARG001
    client = _client(auth_disabled=True)
    assert "set-cookie" not in client.get("/").headers
    assert "set-cookie" not in client.get("/breakfast/pancake-dutch-baby").headers
    cookie = client.get("/me/whoami").headers["set-cookie"]
    assert cookie.startswith("recipes_csrf=") and "SameSite=strict" in cookie
    assert "Secure" in cookie and "HttpOnly" not in cookie


def test_unknown_recipe_not_logged(logged: list[object]) -> None:  # noqa: ARG001
    client = _client(auth_disabled=True)
    r = client.post("/me/log", data={"slug": "nope/nope"}, headers=CSRF)
    assert r.status_code == 404


def test_recipe_page_has_hidden_owner_widget(logged: list[object]) -> None:  # noqa: ARG001
    html = _client(auth_disabled=False).get("/breakfast/pancake-dutch-baby").text
    assert 'data-owner data-slug="breakfast/pancake-dutch-baby" hidden' in html


def test_strangers_get_a_private_page_and_owners_a_whoami(logged: list[object]) -> None:  # noqa: ARG001
    stranger = _client(auth_disabled=False)
    page = stranger.get("/me", headers={"Accept": "text/html"})
    assert page.status_code == 403 and "This page is private" in page.text
    denied = stranger.get("/me/whoami")
    assert denied.status_code == 403 and "set-cookie" not in denied.headers
    assert _client(auth_disabled=True).get("/me/whoami").json() == {"owner": True}


def test_header_has_cart_menu_and_person(logged: list[object]) -> None:  # noqa: ARG001
    html = _client(auth_disabled=False).get("/").text
    assert 'data-panel-toggle="menu"' in html and "data-person" in html
    assert 'href="/#bread"' in html  # the menu's category chips


def test_list_adds_are_counted_by_current_slug(monkeypatch: pytest.MonkeyPatch) -> None:
    bumped: list[tuple[str, str]] = []
    monkeypatch.setattr(counts, "bump", lambda slug, kind, **_k: bumped.append((slug, kind)))
    client = _client(auth_disabled=False)
    # Public: no sign-in and no CSRF token.
    assert client.post("/count/list", data={"slug": "breakfast/granola"}).status_code == 204
    # A moved recipe's old path counts toward where it lives now.
    client.post("/count/list", data={"slug": "breakfast/pancakes-german-dutch-baby"})
    assert client.post("/count/list", data={"slug": "nope/nope"}).status_code == 204
    assert bumped == [("breakfast/granola", "list"), ("breakfast/pancake-dutch-baby", "list")]


def test_me_lists_the_most_added(logged: list[object], monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: ARG001
    monkeypatch.setattr(
        counts, "top", lambda kind, **_k: [("breakfast/granola", 4)] if kind == "list" else []
    )
    page = _client(auth_disabled=True).get("/me").text
    assert "Most added to a shopping list" in page
    assert '<a href="/breakfast/granola">Granola</a> <span class="muted small">4</span>' in page
