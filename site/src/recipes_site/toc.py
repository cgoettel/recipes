"""Generate the README's recipe list from the recipe files.

The README keeps its hand-written intro; everything between the two markers is
generated from the folders and each recipe's front matter, the same data the
site reads (`catalog.py`). CI runs this on every push: on a merge request it
fails when the list is stale, and on `main` it commits the regenerated list.

    python -m recipes_site.toc [--check] [CONTENT_DIR]
"""

from __future__ import annotations

import sys
from pathlib import Path

from recipes_site import catalog

START = (
    "<!-- recipes:start: generated from the recipe files by CI."
    " Edit the recipes, not this list. -->"
)
END = "<!-- recipes:end -->"

# A line of text under a section's heading, keyed by folder path.
SECTION_NOTES = {
    "drinks/sodas": (
        "[Notes on soda making, techniques, etc.](drinks/sodas/README.md) Further notes can be"
        " found in [brew-day-notes/](drinks/sodas/brew-day-notes/)."
    ),
}


def _rows_markdown(rows: list[catalog.Row]) -> list[str]:
    out = []
    for row in rows:
        if row.label:
            out.append(f"- {row.label}")
            out.extend(f"  - [{shown}]({entry.slug}.md)" for entry, shown in row.items)
        else:
            out.extend(f"- [{shown}]({entry.slug}.md)" for entry, shown in row.items)
    return out


def render(cat: catalog.Catalog) -> str:
    lines: list[str] = [START, ""]
    for category in cat.categories:
        lines += [f"## {category.title}", ""]
        for sub in category.subcategories:
            if sub.title:
                lines += [f"### {sub.title}", ""]
                folder = sub.entries[0].slug.rsplit("/", 1)[0]
                if folder in SECTION_NOTES:
                    lines += [SECTION_NOTES[folder], ""]
            lines += _rows_markdown(sub.rows) + [""]
    lines.append(END)
    return "\n".join(lines) + "\n"


def updated_readme(readme: str, listing: str) -> str:
    """The README with its recipe list replaced, keeping the intro as written."""
    if START in readme and END in readme:
        head = readme[: readme.index(START)]
        tail = readme[readme.index(END) + len(END) :].lstrip("\n")
    else:
        # First run: the list starts at the first category heading.
        cut = readme.find("\n## ")
        head = readme if cut < 0 else readme[: cut + 1]
        tail = ""
    return head.rstrip("\n") + "\n\n" + listing + ("\n" + tail if tail else "")


def main(argv: list[str]) -> int:
    check = "--check" in argv
    args = [a for a in argv if not a.startswith("--")]
    content_dir = Path(args[0]) if args else Path.cwd()
    readme_path = content_dir / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    new = updated_readme(readme, render(catalog.load(content_dir)))
    if new == readme:
        print("README recipe list is current.")
        return 0
    if check:
        print(
            "README.md's recipe list is out of date. It's generated from the recipe files:"
            " run `uv --directory site run python -m recipes_site.toc ..` (CI does this on main)."
        )
        return 1
    readme_path.write_text(new, encoding="utf-8")
    print("README recipe list regenerated.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
