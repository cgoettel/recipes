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


def test_badge_counts_the_links_in_the_list(tmp_path: Path) -> None:
    import json

    cat = catalog.load(ROOT)
    # Every link in the list is a recipe, except the soda notes under their heading.
    notes = sum(n.count("](") for n in toc.SECTION_NOTES.values())
    recipes = toc.render(cat).count("](") - notes
    assert toc.count(cat) == recipes
    assert json.loads(toc.badge(cat)) == {
        "schemaVersion": 1,
        "label": "recipes",
        "message": str(recipes),
        "color": "orange",
    }

    # The CLI writes the same badge for whatever folder it's given.
    (tmp_path / "breakfast").mkdir()
    (tmp_path / "breakfast" / "toast.md").write_text("# Toast\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Recipes\n", encoding="utf-8")
    out = tmp_path / "recipe-count.json"
    toc.main([f"--count-file={out}", str(tmp_path)])
    assert json.loads(out.read_text())["message"] == "1"
