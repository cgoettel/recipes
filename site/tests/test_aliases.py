"""Moved recipes keep their links and history (#19)."""

import datetime as dt
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from recipes_site import catalog, cooklog, counts, renames
from recipes_site.app import create_app
from recipes_site.config import Settings

RECIPE = """---
{front}
---

# {title}

## Ingredients

- 1 cup flour

## Instructions

1. Mix.
"""


def _write(root: Path, rel: str, title: str, front: str = "serves: 2") -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(RECIPE.format(front=front, title=title), encoding="utf-8")


@pytest.fixture
def content(tmp_path: Path) -> Iterator[Path]:
    _write(
        tmp_path,
        "sauces/hot-sauces/habanero.md",
        "Habanero",
        "aliases: [sauces/salsas/sauce-habanero, /sauces/salsas/old-habanero.md]",
    )
    _write(tmp_path, "breakfast/granola.md", "Granola")
    catalog.cached.cache_clear()
    yield tmp_path
    catalog.cached.cache_clear()


def test_catalog_maps_aliases(content: Path) -> None:
    cat = catalog.load(content)
    new = "sauces/hot-sauces/habanero"
    assert cat.aliases == {
        "sauces/salsas/sauce-habanero": new,
        "sauces/salsas/old-habanero": new,
    }
    assert cat.current("sauces/salsas/sauce-habanero") == new
    assert cat.current(new) == new
    assert cat.current("nope/nothing") is None
    assert cat.slugs_for(new) == [new, "sauces/salsas/sauce-habanero", "sauces/salsas/old-habanero"]
    assert catalog.check(content) == []


def test_check_rejects_bad_aliases(tmp_path: Path) -> None:
    _write(tmp_path, "breakfast/granola.md", "Granola", "aliases: [breakfast/oats]")
    _write(
        tmp_path, "breakfast/muesli.md", "Muesli", "aliases: [breakfast/oats, breakfast/granola]"
    )
    _write(tmp_path, "breakfast/bad.md", "Bad", "aliases: breakfast/x")
    found = catalog.check(tmp_path)
    assert any("`breakfast/granola` is a live recipe" in p for p in found)
    assert any("`breakfast/oats` is also claimed" in p for p in found)
    assert any("bad.md: `aliases` should be a list" in p for p in found)


@pytest.fixture
def client(content: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(counts, "bump", lambda *_a, **_k: None)
    app = create_app(Settings(content_dir=content, auth_disabled=True))
    return TestClient(app, follow_redirects=False)


def test_old_path_redirects(client: TestClient) -> None:
    r = client.get("/sauces/salsas/sauce-habanero?scale=2")
    assert r.status_code == 301
    assert r.headers["location"] == "/sauces/hot-sauces/habanero?scale=2"
    assert client.get("/sauces/salsas/sauce-habanero.md").status_code == 301


def test_list_resolves_old_paths(client: TestClient) -> None:
    r = client.get("/list?r=sauces/salsas/sauce-habanero@1")
    assert r.status_code == 200
    assert "Habanero" in r.text


def test_cook_log_reads_old_paths(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    asked: list[list[str]] = []

    def status(slugs: list[str]) -> cooklog.Status:
        asked.append(slugs)
        return cooklog.Status(count=1, last=dt.date(2026, 10, 1))

    monkeypatch.setattr(cooklog, "status", status)
    monkeypatch.setattr(cooklog, "made_slugs", lambda: {"sauces/salsas/sauce-habanero"})
    monkeypatch.setattr(
        cooklog,
        "recent",
        lambda *_a, **_k: [
            cooklog.Made("sauces/salsas/sauce-habanero", dt.date(2026, 10, 1), None)
        ],
    )
    monkeypatch.setattr(
        counts,
        "top",
        lambda *_a, **_k: [("sauces/salsas/sauce-habanero", 2), ("sauces/hot-sauces/habanero", 3)],
    )
    client.get("/me/status?slug=sauces/hot-sauces/habanero")
    assert asked == [
        ["sauces/hot-sauces/habanero", "sauces/salsas/sauce-habanero", "sauces/salsas/old-habanero"]
    ]
    page = client.get("/me").text
    assert 'href="/sauces/hot-sauces/habanero"' in page
    assert 'Habanero</a> <span class="muted small">5</span>' in page
    # Made under its old path, so it isn't "untested"; Granola is.
    untested = page.split("Untested", 1)[-1]
    assert "Granola" in untested
    assert "Habanero" not in untested


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "commit.gpgsign=false",
            *args,
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "t")
    _write(tmp_path, "sauces/salsas/sauce-habanero.md", "Habanero")
    _write(tmp_path, "breakfast/granola.md", "Granola")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "base")
    return tmp_path


def _move(repo: Path, front: str) -> str:
    base = _git(repo, "rev-parse", "HEAD")
    (repo / "sauces/hot-sauces").mkdir(parents=True)
    _git(repo, "mv", "sauces/salsas/sauce-habanero.md", "sauces/hot-sauces/habanero.md")
    _write(repo, "sauces/hot-sauces/habanero.md", "Habanero", front)
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "move")
    return base


def test_guard_fails_a_move_without_an_alias(repo: Path) -> None:
    base = _move(repo, "serves: 2")
    found = renames.problems(repo, base)
    assert len(found) == 1
    assert "aliases: [sauces/salsas/sauce-habanero]" in found[0]
    assert renames.main([base, str(repo)]) == 1


def test_guard_passes_a_move_with_an_alias(repo: Path) -> None:
    base = _move(repo, "aliases: [sauces/salsas/sauce-habanero]")
    assert renames.problems(repo, base) == []


def test_guard_accepts_a_retired_recipe(repo: Path) -> None:
    base = _git(repo, "rev-parse", "HEAD")
    _git(repo, "rm", "-q", "breakfast/granola.md")
    (repo / "site").mkdir()
    (repo / "site/retired-recipes.txt").write_text("# gone\nbreakfast/granola\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "retire")
    assert renames.problems(repo, base) == []


def test_guard_skips_without_a_base() -> None:
    assert renames.main(["0" * 40]) == 0


def test_guard_fails_a_second_move_that_drops_an_alias(repo: Path) -> None:
    _move(repo, "aliases: [sauces/salsas/sauce-habanero]")
    base = _git(repo, "rev-parse", "HEAD")
    _git(repo, "mv", "sauces/hot-sauces/habanero.md", "sauces/hot-sauces/habanero-sauce.md")
    _write(
        repo,
        "sauces/hot-sauces/habanero-sauce.md",
        "Habanero",
        "aliases: [sauces/hot-sauces/habanero]",
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "move again")
    found = renames.problems(repo, base)
    assert len(found) == 1
    assert "`sauces/salsas/sauce-habanero` no longer leads anywhere" in found[0]


def test_check_rejects_a_partial_alias(tmp_path: Path) -> None:
    _write(tmp_path, "breakfast/granola.md", "Granola", "aliases: [granola]")
    assert any("should be a full old path" in p for p in catalog.check(tmp_path))


def test_list_lists_a_moved_recipe_once(client: TestClient) -> None:
    r = client.get("/list?r=sauces/salsas/sauce-habanero@1&r=sauces/hot-sauces/habanero@2")
    assert r.text.count('href="/sauces/hot-sauces/habanero') == 1
