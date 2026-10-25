from pathlib import Path

from recipes_site import catalog, toc

ROOT = Path(__file__).resolve().parents[2]


def test_regenerating_twice_changes_nothing() -> None:
    # The committed README may lag a branch's recipes; main's CI catches it up.
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    once = toc.updated_readme(readme, toc.render(catalog.load(ROOT)))
    assert toc.updated_readme(once, toc.render(catalog.load(ROOT))) == once


def test_update_keeps_the_intro_and_replaces_only_the_list() -> None:
    old = "# Recipes\n\nMy intro.\n\n## Bread\n\n- [Old](bread/old.md)\n"
    first = toc.updated_readme(
        old, f"{toc.START}\n\n## Bread\n\n- [New](bread/new.md)\n\n{toc.END}\n"
    )
    assert first.startswith("# Recipes\n\nMy intro.\n\n" + toc.START)
    assert "Old" not in first and "[New]" in first
    again = toc.updated_readme(
        first, f"{toc.START}\n\n## Bread\n\n- [Newer](bread/x.md)\n\n{toc.END}\n"
    )
    assert "My intro." in again and "[New]" not in again and again.count(toc.START) == 1


def test_families_nest_in_the_readme() -> None:
    listing = toc.render(catalog.load(ROOT))
    assert "- Pancakes\n  - [Bacon cornmeal](breakfast/pancakes-bacon-cornmeal.md)" in listing
    assert "- [Almond](bread/bread-almond.md)" in listing  # Bread under Bread drops the family
