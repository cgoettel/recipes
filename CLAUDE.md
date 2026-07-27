# Recipes repo

Personal recipe collection in markdown. Each recipe is its own file under a category folder; the [README](README.md) is the canonical table of contents.

## Working in this repo

- **Work directly in `main`.** No feature branches, no worktrees, no MRs. Edit, commit, push.
- Conventional commit prefixes: `feat:` for new recipes, `fix:` for corrections, `refactor:` for reorganization, `docs:` for README-only changes.
- **The repo is shared publicly.** README, recipe files, and any markdown a cook would read should be written for a general audience — neutral voice, "you" or imperative form for instructions, no third-person asides about the owner. Save personal preferences and owner-specific context for this file (`CLAUDE.md`) instead.

## Cook's preferences

Persistent preferences that should shape suggestions, edits, and new recipes across this repo.

**Philosophy.** Recipes are for remembering ingredients and proportions; technique and method are what actually matter. When writing or editing, lean toward describing *how* and *why* something is done, not just the sequence — method-level guidance is worth the line. The cook works by feel ("two spoonfuls," "half a jar," "quarter can"); recipes should give ranges rather than tweezer-precise grams unless chemistry demands it (bread, candy).

**Alcohol.** Used purely for flavor, never for effect. When choosing wine, beer, or spirits, pick for what they contribute to the dish — flavor depth, acid, fat-cutting, aromatic survivability through aging or heat — never "what's open" or "use up the cheap stuff."

**Anti-preferences (hard nos).**

- **Caraway.** Skip entirely, including in territory where it's the default (German, Eastern European, rye breads).
- **Kimchi.** Out as an ingredient or a pairing. Other Korean food is fine.
- **Sweet meat.** Fruit-with-meat pairings, honey-glazed savories, fruit-stuffed pork, etc. don't land. Push savory/funky/acid layers instead.
- **Warming spices in Western savory cooking.** Cinnamon, allspice, cloves in American/European meat dishes (chili, roasts, etc.) are out. **Nutmeg is the odd exception** and is welcome. **South Asian / Indian cooking is fully exempt** — cinnamon, cloves, cardamom bloomed in fat are core technique there and explicitly welcome (Kerala coconut curry, basmati pulao, etc.). The aversion is to warm spices reading as "sweet" in Western savories, not to the spices themselves.

**Active interests.**

- **Fermentation.** Sauerkraut, pickles, and fermented hot sauces are an active build-out area. Fermentation as a technique is already trusted ground — see also the soda program in `drinks/sodas/`.
- **Hot dog eating contest, 2027.** Friend-group goal of 365 hot dogs across the year. Treat brat-, dog-, mustard-, sausage-, bun-, and topping-adjacent recipes as high-priority work for the duration.

**Reference profiles and brand benchmarks.**

- **Fermented and pickled vegetables — target bright/crisp/less-funky, not deep funk.** The reference points are **Claussen kraut** (best both fresh and in cooking) and **Grillo's pickles** (dill and hot spears). The cook will go out of the way to a grocery store stocking them. **Bubbies is explicitly out** — too deeply funky, too fully fermented. Design recipes for the Claussen/Grillo's end of the spectrum: shorter ferments, slightly higher salt (closer to 2.5% than 2%), thicker cuts, eaten young, stored cold.
- **Hot sauce — multiple profile slots, not "one best."** Distinct bottles for distinct cuisine pairings:
  - **Homemade habanero** — fresh, fruity, decidedly Mexican; for Mexican food. Multiple-friends-confirm "best ever."
  - **Yellow Bird habanero** — matured, savory-deeper (from carrot + cooking, not fermentation); for American and German meals.
  - **Fermented hot sauces** (e.g., the Fresno and aji amarillo recipes in this repo) — funky/lacto profile; a third slot for slow-cooked meats, charcuterie, grilled food.

**Fermentation constraint: house temperature.**

The house is climate-controlled at 21.5–24°C (~71–75°F) and there is no cooler microclimate available (the cigar tupperdor runs a degree or two warmer too). This is the warm end of the lacto-fermentation comfort range — textbook ideal is 60–65°F (15.5–18.5°C) — so ferments run **faster and tend funkier** than reference profiles like Claussen would suggest. Recipes should compensate: shorter ferment windows, higher salt percentages, thicker cuts, and frequent tasting from day 5 onward to catch the right moment before it tips. Historical room-level temperature data lives in `~/git/smart-home/` Grafana if a cooler spot is ever worth identifying.

## Adding a recipe

1. Pick the right category folder (see structure below). Folder names mirror README friendly names exactly — what you see in the README is the folder name.
2. Filename is kebab-case, no special characters. Examples: `chiles-gueros-rellenos-de-camaron.md`, `roast-chuck.md`.
3. File structure:
   - `# Title` (H1)
   - Optional intro / attribution paragraph
   - `## Ingredients` — bulleted list
   - `## Instructions` (or `## Directions` / `## Steps` — existing recipes vary) — a numbered list. Write `1.` on every line if that's easier; the fleet-wide `mdformat --number` pre-commit hook renumbers ordered lists sequentially (1, 2, 3) on commit, so the committed source always ends up numbered either way.
   - Optional `## Notes` section
4. Add a link in the README under the correct subsection, in alphabetical order.

## Directory structure

Folder names match README friendly names exactly so navigation maps 1:1 between filesystem and TOC.

```
bread/
breakfast/
drinks/
  sodas/                          ← has its own README + brew-day-notes/
  syrups/                         ← cocktail syrups, cordials, oleo-saccharums
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
  pickled/                        ← lacto-ferments (sauerkraut) and vinegar pickles together
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

- Fractions and dashes are Unicode (`½`, `–`, `¼`), corpus-wide. Older recipes used HTML entities (`&frac12;`, `&ndash;`); the `mdformat` pre-commit hook converts them, so entities typed into a new recipe will be rewritten on commit rather than preserved.
- Cross-recipe links use relative paths. Examples:
  - Same folder: `[birria de res](birria-de-res.md)`
  - Sibling folder: `[meatballs](../italian/meatballs.md)`
  - Different top-level: `[red sauce](../../sauces-and-condiments/sauces/sauce-red.md)`

## Recipe conventions

Ingredient defaults (salted butter, all-purpose flour, etc.), knife-cut sizing, and meat-seasoning conventions live in the top of [README.md](README.md) — read that section before writing or editing a recipe so the resulting file matches house style.

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
