# Recipes repo

Personal recipe collection in markdown. Each recipe is its own file under a category folder; the [README](README.md) is the canonical table of contents.

## Working in this repo

- **Work directly in `main`.** No feature branches, no worktrees, no MRs. Edit, commit, push.
- Push immediately after committing (per global convention).
- Conventional commit prefixes: `feat:` for new recipes, `fix:` for corrections, `refactor:` for reorganization, `docs:` for README-only changes.

## Adding a recipe

1. Pick the right category folder (see structure below). Folder names mirror README friendly names exactly — what you see in the README is the folder name.
2. Filename is kebab-case, no special characters. Examples: `chiles-gueros-rellenos-de-camaron.md`, `roast-chuck.md`.
3. File structure:
   - `# Title` (H1)
   - Optional intro / attribution paragraph
   - `## Ingredients` — bulleted list
   - `## Instructions` (or `## Directions` / `## Steps` — existing recipes vary) — numbered list using `1.` for each line so markdown auto-numbers
   - Optional `## Notes` section
4. Add a link in the README under the correct subsection, in alphabetical order.

## Directory structure

Folder names match README friendly names exactly so navigation maps 1:1 between filesystem and TOC.

```
bread/
breakfast/
drinks/
  sodas/                          ← has its own README + brew-day-notes/
entrees/
  american/
  curries/                        ← South Asian + Caribbean
  east-asian/
  italian/
  mediterranean/
  mexican/
  soups-and-stews/
household/
sauces-and-condiments/
  dressings/
  salsas/
  sauces/
sides-and-starters/
sweets/
  cakes/
  confections/
  cookies/
  pies/
```

## Categorization rules of thumb

- **Chili → American**, not soups/stews. Owner doesn't think of chili as soup.
- **Sweet potato pie → side**, not dessert. Thanksgiving side dish in this household, served during the meal.
- **Meatball subs → American**; **meatballs → Italian** (spaghetti-and-meatballs lineage).
- **Sopapillas → Sweets / Confections**, not Mexican entrée.
- **Yorkshire pudding → side**, not entrée.
- Single-item cuisine bins (e.g., `entrees/mediterranean/` is just chermoula lamb chops) are fine — they'll grow.

## Recipe formatting quirks

- Older recipes use HTML entities (`&frac12;`, `&ndash;`, `&frac14;`); newer ones use Unicode (`½`, `–`, `¼`). Either is fine — match the existing file's style if editing.
- Cross-recipe links use relative paths. Examples:
  - Same folder: `[birria de res](birria-de-res.md)`
  - Sibling folder: `[meatballs](../italian/meatballs.md)`
  - Different top-level: `[red sauce](../../sauces-and-condiments/sauces/sauce-red.md)`

## README intro conventions (already in [README.md](README.md))

- Mince = super fine (<¼"), dice = ¼–½", chopped = >½".
- Default: salted butter, large eggs.
- "Flour" = all-purpose, "sugar" = white granulated.
- Non-ground beef is seasoned and rested before cooking; slow-cooks are seared first.
- Ground beef is seasoned with Lawry's seasoned salt + fresh cracked pepper.
