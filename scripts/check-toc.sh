#!/bin/sh
# Guard the README's canonical table of contents against drift.
#
# Two checks:
#   1. Orphans   — every recipe file on disk is linked from the README.
#   2. Dead links — every relative .md link in the README resolves to a file.
#
# Runnable locally (`sh scripts/check-toc.sh`) and in CI. Exits non-zero on any
# problem so a push that adds an unlinked recipe or a stale link fails loudly.

set -eu
cd "$(git rev-parse --show-toplevel)"

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

# Recipe files that must appear in the table of contents. Excluded: every
# README, the repo meta docs, and the soda brew-day notes (logs, not recipes).
find . -type f -name '*.md' \
  ! -path './.git/*' \
  ! -name 'README.md' \
  ! -name 'CLAUDE.md' \
  ! -name 'contributing.md' \
  ! -path './drinks/sodas/brew-day-notes/*' \
  | sed 's|^\./||' | sort > "$tmp/recipes"

# Relative .md links in the canonical README (repo-root-relative paths).
grep -oE '\]\([^)]+\.md\)' README.md | sed -E 's/^\]\(//; s/\)$//' | sort -u > "$tmp/links"

status=0

orphans=$(grep -Fxv -f "$tmp/links" "$tmp/recipes" || true)
if [ -n "$orphans" ]; then
  echo "ERROR: recipe files not linked in README.md:"
  echo "$orphans" | sed 's/^/  /'
  status=1
fi

dead=""
while IFS= read -r link; do
  [ -z "$link" ] && continue
  [ -f "$link" ] || dead="${dead}${link}
"
done < "$tmp/links"
if [ -n "$dead" ]; then
  echo "ERROR: README.md links pointing to missing files:"
  printf '%s' "$dead" | sed 's/^/  /'
  status=1
fi

if [ "$status" -eq 0 ]; then
  echo "TOC OK: $(wc -l < "$tmp/recipes" | tr -d ' ') recipes, all linked, no dead links."
fi
exit "$status"
