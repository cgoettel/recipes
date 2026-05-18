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
  caribbean/                      ← Trinidadian, Dominican, etc.
  curries/                        ← South Asian (butter chicken, etc.)
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

## Attribution / name lineage

- **"Mom" / "Mom's"** in a recipe title or filename = LeAnn Goettel. Existing entries: `chili-moms.md`, `chocolate-chip-cookies-moms.md`, `bread-honey-wheat-leann.md`, `cinnamon-rolls-leann.md`, `lasagna-moms.md`, `salsa-moms.md`, `pie-filling-moms-apple.md`. Some Drive docs say "LeAnn" and some say "Mom" for the same author.
- **"Grant" / "Grant's"** = Grant Massey. He vibe-cooks, so his recipes were reconstructed by watching him: `burros-grants.md`, `chocolate-chip-cookies-grants.md`. His own kids don't have them written down.

## Importing from Bryce's Google Drive

Bryce (bryce.goettel@gmail.com) owns the shared Google Drive `Recipes/` folder; the user also has top-level `.gdoc` files in their own My Drive root. Periodically sync net-new recipes worth incorporating.

**Last sync: 2026-05-17** — 25 recipes imported, Caribbean entrée folder carved out of curries. See `git log -- entrees/caribbean/ bread/bread-baguette-paul-hollywood.md` for the haul.

**Process**: read `.gdoc` files via the Drive MCP (`mcp__claude_ai_Google_Drive__read_file_content`). The `.gdoc` files in the filesystem are 178-byte JSON pointer files — they contain a `doc_id`, not content. Extract `doc_id` with `python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['doc_id'])" <file>` and feed to the MCP.

**Gotchas observed 2026-05-17:**

- **Some docs are images, not text.** `read_file_content` returns an empty string for these. Ask the user to open the doc and screenshot it, then `/check-screenshot`. (The 2026-05-17 moro de guandules recipe came in this way.)
- **Doc titles lie.** "CHUDS - Mississippi Pot Roast" was Alabama BBQ chicken; "Dominican Chicken 2 (pollo guisado)" was chicken soup (sopa de pollo). Always read the body before deciding category/filename.
- **Some "recipes" are just a YouTube URL.** Write a minimal link-only file in the matching category — see `entrees/american/chicken-leroy-and-lewis.md` for the format the user accepts.
- **AI-generated prose creeps in.** Flag doc bodies that read overly literary ("memory and mystery," nostalgic Nonna vignettes) before importing — may not be a real family recipe. On 2026-05-17 the user dropped a "Sunday Gravy" doc for this reason.
- **Drive's folder ≠ repo's folder.** Drive often files rice and brunch items under `/Entrees`. Apply this repo's categorization rules instead (Dominican rice → sides; biscuits-and-gravy → breakfast).
- **Triage strategy that worked**: pre-veto from filenames (most aren't wanted), then fetch only the keeps and skim for content quality. Batch-fetching everything is wasteful.
