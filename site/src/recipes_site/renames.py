"""CI guard: a recipe that is renamed, moved or deleted leaves its old path behind.

A recipe's path is its URL and the key for its cook-log history, so a rename
without an alias breaks links and sends a cooked recipe back to "untested."
This compares a base commit with HEAD and fails for any recipe file that went
away unless its old path is now an alias (or a recipe again), or is listed in
site/retired-recipes.txt as removed on purpose.

    python -m recipes_site.renames <base-sha> [<repo-root>]
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

from recipes_site import catalog

RETIRED = Path("site/retired-recipes.txt")


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout


def changed_recipes(repo: Path, base: str) -> list[tuple[str, str, str | None]]:
    """(status, old path, new path or None) for recipe files modified, renamed or deleted."""
    # -z: NUL-separated and unquoted, so paths with accents ("Åke") come through as-is.
    out = _git(repo, "diff", "-z", "-M", "--name-status", "--diff-filter=DRM", base, "HEAD")
    fields = out.split("\0")
    changes: list[tuple[str, str, str | None]] = []
    i = 0
    while i < len(fields) and fields[i]:
        status = fields[i][0]
        old = fields[i + 1]
        new = fields[i + 2] if status == "R" else None
        i += 3 if status == "R" else 2
        if catalog.is_recipe_path(old) and old.count("/") in (1, 2):
            changes.append((status, old, new))
    return changes


def aliases_at(repo: Path, base: str, path: str) -> list[str]:
    """The aliases a recipe file carried at base, so a second move can't drop them."""
    try:
        meta, _ = catalog.split_front_matter(_git(repo, "show", f"{base}:{path}"))
    except subprocess.CalledProcessError, ValueError, yaml.YAMLError:
        return []
    return catalog.parse_aliases(meta.get("aliases"))


def retired(repo: Path) -> set[str]:
    path = repo / RETIRED
    if not path.is_file():
        return set()
    lines = (ln.split("#", 1)[0].strip() for ln in path.read_text(encoding="utf-8").splitlines())
    return {catalog.alias_slug(ln) for ln in lines if ln}


def problems(repo: Path, base: str) -> list[str]:
    cat = catalog.load(repo)
    gone = retired(repo)
    found = []
    for status, old, new in changed_recipes(repo, base):
        here = new or old
        # The file's own old path (if it moved or went away), and every alias it had.
        paths = [old[:-3]] if status in "DR" else []
        paths += aliases_at(repo, base, old)
        for slug in paths:
            if cat.current(slug) or slug in gone:
                continue
            if status == "R" and slug == old[:-3] and catalog.is_recipe_path(here):
                fix = f"add `aliases: [{slug}]` to {here}'s front matter"
            elif status != "D" and catalog.is_recipe_path(here):
                fix = f"keep `{slug}` in {here}'s `aliases`"
            else:
                fix = (
                    f"add `{slug}` to the `aliases` of the recipe that replaces it, or to {RETIRED}"
                )
            found.append(f"{old}: `{slug}` no longer leads anywhere: {fix}")
    return found


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    base = argv[0]
    repo = Path(argv[1]) if len(argv) > 1 else Path()
    if not base.strip("0"):
        print("renames: no base commit (a new branch or a manual pipeline); nothing to compare")
        return 0
    known = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "-e", f"{base}^{{commit}}"], capture_output=True
    )
    if known.returncode != 0:
        print(f"renames: base {base} isn't in this clone (a force-push?); nothing to compare")
        return 0
    found = problems(repo, base)
    for line in found:
        print(f"renames: {line}")
    if not found:
        print("renames: every moved or deleted recipe left its path behind")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
