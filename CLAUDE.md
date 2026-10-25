# Recipes repo

Personal recipe collection in markdown. Each recipe is its own file under a category folder; the [README](README.md) is the canonical table of contents.

## Working in this repo

- **GitLab is the home.** [colby.goettel/recipes](https://gitlab.com/colby.goettel/recipes) is canonical. GitHub ([cgoettel/recipes](https://github.com/cgoettel/recipes)) is a read-only mirror that CI force-pushes on every push to `main`, so anything merged on GitHub is overwritten. Issues and contributions go to GitLab.
- **Every change goes through a `git worktree`** — global rule, no exceptions (worktrees everywhere, every time). Branch off `origin/main` in a worktree, commit there, then merge to `main` and push; never edit or commit from the main checkout. **No MR is required**: commit, fast-forward `main`, and push. The worktree step is not optional.
- Conventional commit prefixes: `feat:` for new recipes, `fix:` for corrections, `refactor:` for reorganization, `docs:` for README-only changes.
- Issue housekeeping (milestones, labels) follows the fleet conventions in the `glab` skill. The `Maintenance` and `Creations` milestones are evergreen buckets; never close them.
- **The repo is shared publicly, and that includes this file.** Recipe files and any markdown a cook would read should be written for a general audience — neutral voice, "you" or imperative form for instructions, no third-person asides about the owner. The README intro is the exception: it's the owner's own first-person voice, written and maintained by him, and it stays that way. Never put contact details (email addresses, phone numbers) for anyone in the repo, `CLAUDE.md` included. Personal context that shouldn't be public belongs in agent memory, not here.

## Operations

Git is the database for recipe text: rollback is `git revert`, and copies live on GitLab, GitHub, and every clone. The moving parts:

- **The site** ([recipes.skalchemy.com](https://recipes.skalchemy.com), app in `site/`, see [site/README.md](site/README.md)). Every push to `main`, recipe edits included, builds an image with the recipes baked in and tags it `main-<pipeline iid>-<sha>`. Flux image automation in smart-home commits the newest tag (`kubernetes/recipes/app/values.yaml`), the api pod's init container runs the migrations, and the `verify_live` CI job goes green once the public `/health` reports the build. So a pushed recipe goes live in a few minutes with no other step, and a green pipeline means it's serving. Roll back with `git revert` of the `chore(deploy)` commit in smart-home. Changes under `site/` go through an MR with green CI (`~/.claude/scripts/merge-mr`); recipe edits still go straight to `main`. `site_test` parses every recipe, so a recipe the parser can't read fails CI before it ships. The site follows the fleet conventions in the `unified-design` skill.
- **CI** (`.gitlab-ci.yml`). `check_toc` runs `scripts/check-toc.sh` on every push. `mirror_to_github` force-pushes `main` to GitHub, authenticating with the `GITHUB_DEPLOY_KEY` File-type CI variable, an SSH private key whose public half is a write-enabled deploy key on the GitHub repo. To rotate it: generate a new ed25519 key pair, replace the deploy key under the GitHub repo's Settings → Deploy keys (write access), and replace the private key in the `GITHUB_DEPLOY_KEY` variable (GitLab Settings → CI/CD → Variables, keeping it File type). The job re-adds the trailing newline glab strips. If the mirror job fails, `main` on GitLab is still fine; fix the key and re-run the job.
- **Formatting and secrets.** Locally, `mdformat --number` (with GFM and front matter plugins), whitespace fixers, gitleaks, and commitizen run from the owner's global pre-commit hook in dotfiles (`git/.config/git/hooks/pre-commit` and `git/.config/pre-commit/global.yaml`). CI checks the same things for commits made where that hook isn't installed: `check_format` runs the pinned mdformat from `.pre-commit-config.yaml` (on the `manual` stage, so it doesn't run twice locally; keep its versions in step with the global file), and `check_secrets` runs gitleaks over the full history. To fix a `check_format` failure, recommit the file through the global hook, which reformats it.

## Cook's preferences

Persistent preferences that should shape suggestions, edits, and new recipes across this repo.

**Philosophy.** Recipes are for remembering ingredients and proportions; technique and method are what actually matter. When writing or editing, lean toward describing *how* and *why* something is done, not just the sequence — method-level guidance is worth the line. The cook works by feel ("two spoonfuls," "half a jar," "quarter can"); recipes should give ranges rather than tweezer-precise grams unless chemistry demands it (bread, candy).

**Alcohol.** Used purely for flavor, never for effect. When choosing wine, beer, or spirits, pick for what they contribute to the dish — flavor depth, acid, fat-cutting, aromatic survivability through aging or heat — never "what's open" or "use up the cheap stuff."

**Good-enough store-bought.** Frozen gyoza and dumplings are bought, not made. When a restaurant dish centers on them, write the sauce and serving method as the recipe (see `sauces-and-condiments/sauces/dipping-sauce-gyoza.md`), not a from-scratch dumpling. Ask before assuming the same for other components.

**Butter.** Salted is the default, always. A recipe may name an alternative when it genuinely matters, but say why, and expect salted to be used anyway: nobody is buying unsalted butter for one recipe.

**Cooking for guests.** Some dishes get made for people with dietary or religious restrictions (for example, vegan, or no coffee or tea). Those are per-occasion constraints, not house rules. When a request mentions one, honor it everywhere, including hidden sources like black tea as a pickle tannin (use toasted oak cubes or grape leaves instead).

**Grilling.** Grilled recipes get cooked on both charcoal and gas, so write the method for both: call out charcoal technique (wood chunks, char) and give a gas path rather than assuming charcoal. See `sides-and-starters/grilled-artichokes.md`.

**Anti-preferences (hard nos).**

- **Caraway.** Skip entirely, including in territory where it's the default (German, Eastern European, rye breads).
- **Kimchi.** Out as an ingredient or a pairing. Other Korean food is fine.
- **Sweet meat.** Fruit-with-meat pairings, honey-glazed savories, fruit-stuffed pork, etc. don't land. Push savory/funky/acid layers instead.
- **Warming spices in Western savory cooking.** Cinnamon, allspice, cloves in American/European meat dishes (chili, roasts, etc.) are out. **Nutmeg is the odd exception** and is welcome. **South Asian / Indian cooking is fully exempt** — cinnamon, cloves, cardamom bloomed in fat are core technique there and explicitly welcome (Kerala coconut curry, basmati pulao, etc.). The aversion is to warm spices reading as "sweet" in Western savories, not to the spices themselves.

**What this repo is.** A catch-all for everything the owner cooks, brews, or mixes, not a set of programs. Fermentation (sauerkraut, pickles, fermented hot sauces, mustard) and sodas (`drinks/sodas/`) are both dormant; the recipes and reference profiles below still apply whenever they come back.

**Active interests.**

- **Hot dog eating contest, 2027.** Friend-group goal of 365 hot dogs across the year. Treat brat-, dog-, mustard-, sausage-, bun-, and topping-adjacent recipes as high-priority work for the duration.

**Reference profiles and brand benchmarks.**

- **Fermented and pickled vegetables — target bright/crisp/less-funky, not deep funk.** The reference points are **Claussen kraut** (best both fresh and in cooking) and **Grillo's pickles** (dill and hot spears). The cook will go out of the way to a grocery store stocking them. **Bubbies is explicitly out** — too deeply funky, too fully fermented. Design recipes for the Claussen/Grillo's end of the spectrum: shorter ferments, slightly higher salt (closer to 2.5% than 2%), thicker cuts, eaten young, stored cold.

- **Hot sauce — multiple profile slots, not "one best."** Distinct bottles for distinct cuisine pairings:

  - **Homemade habanero** — fresh, fruity, decidedly Mexican; for Mexican food. Multiple-friends-confirm "best ever."
  - **Yellow Bird habanero** — matured, savory-deeper (from carrot + cooking, not fermentation); for American and German meals.
  - **Fermented hot sauces** (e.g., the Fresno and aji amarillo recipes in this repo) — funky/lacto profile; a third slot for slow-cooked meats, charcuterie, grilled food.

- **Iced and sun tea — semi-sweet, sweetened with agave.** Confirmed 2026-08-01 on a 2 L sun tea batch: the semi-sweet row of the chart in `drinks/tea-sun.md` (3½ Tbsp agave per 2 L, ~12 g sugar per 8 oz glass) landed exactly right — "incredible." Agave over honey or granulated sugar for tea; it dissolves cold and stays out of the tea's way. Default to that level when sweetening tea unless asked otherwise, and treat the full-sweet and Southern-diner rows as reference points rather than targets.

**Fermentation constraint: house temperature.**

The house is climate-controlled at 21.5–24°C (~71–75°F) and there is no cooler microclimate available. This is the warm end of the lacto-fermentation comfort range — textbook ideal is 60–65°F (15.5–18.5°C) — so ferments run **faster and tend funkier** than reference profiles like Claussen would suggest. Recipes should compensate: shorter ferment windows, higher salt percentages, thicker cuts, and frequent tasting from day 5 onward to catch the right moment before it tips.

## Adding a recipe

1. Pick the right category folder (see structure below). Folder names mirror README friendly names exactly — what you see in the README is the folder name.
2. Filename is kebab-case, no special characters. Examples: `chiles-gueros-rellenos-de-camaron.md`, `roast-chuck.md`.
3. File structure:
   - `# Title` (H1)
   - Optional intro / attribution paragraph
   - `## Ingredients` — bulleted list
   - `## Instructions` (or `## Directions` / `## Steps` — existing recipes vary) — a numbered list. Write `1.` on every line if that's easier; the fleet-wide `mdformat --number` pre-commit hook renumbers ordered lists sequentially (1, 2, 3) on commit, so the committed source always ends up numbered either way.
   - Optional `## Notes` section
4. Add a link in the README under the correct subsection, in alphabetical order. CI enforces this: `scripts/check-toc.sh` (a `check_toc` job on every push) fails if any recipe file is missing from the README or the README links a file that no longer exists. Run it locally with `sh scripts/check-toc.sh` before pushing. The script's exclusion list (READMEs, `CLAUDE.md`, `contributing.md`, `drinks/sodas/brew-day-notes/`, and everything under `site/`) is the working definition of "not a recipe": any other new Markdown file needs an exclusion there, or CI fails.
5. Name the file and title after what someone would search for. When a dish has two common names, put both in the title, for example "Dutch Baby (German Pancakes)".

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

- **Units.** Every recipe uses these spellings (swept in #4); the site's parser reads them, and `site_test` fails CI if a recipe stops parsing.

  | Unit                      | Write it as                                                                      |
  | ------------------------- | -------------------------------------------------------------------------------- |
  | Cup, tablespoon, teaspoon | `cup`/`cups`, `tablespoon(s)`, `teaspoon(s)`: never `C`, `T`, `t`, `tbsp`, `tsp` |
  | Ounce, pound              | `oz`, `lb` (no period, no `lbs`)                                                 |
  | Gallon, quart, pint       | `gallon(s)`, `quart(s)`, `pint(s)`                                               |
  | Package                   | `package(s)`                                                                     |
  | Metric                    | `g`, `kg`, `mL`, `L`                                                             |
  | A size, not an amount     | hyphenated: `2-quart pot`, `1-inch piece`                                        |

  Plural above one (`1 cup`, `1½ cups`, `½ cup`); a range takes its top (`1–2 cups`).

- **Gram estimates on bread.** Bread recipes carry estimated weights in parentheses after volume amounts, marked `≈`: `2 cups (≈240 g) flour`. They come from King Arthur's weight chart (flour 120 g a cup, whole wheat 113, water and milk 227, sugar 198, table salt 6 g a teaspoon, yeast 3 g a teaspoon) and feed the baker's-percentage view. Replace an estimate with a real weighing whenever you have one, and drop the `≈`.

- Fractions and dashes are Unicode (`½`, `–`, `¼`), never `1/2` or HTML entities, with no space between a whole number and its fraction (`1½`).

- Cross-recipe links use relative paths. Examples:

  - Same folder: `[birria de res](birria-de-res.md)`
  - Sibling folder: `[meatballs](../italian/meatballs.md)`
  - Different top-level: `[red sauce](../../sauces-and-condiments/sauces/sauce-red.md)`

## Recipe conventions

Ingredient defaults (salted butter, all-purpose flour, etc.), knife-cut sizing, and meat-seasoning conventions live in the top of [README.md](README.md) — read that section before writing or editing a recipe so the resulting file matches house style.

## Attribution / name lineage

**Privacy rule: only people who have died get surnames.** Living people appear by first name only, in recipe titles, filenames, and docs alike (for example "Grant's," not his full name). Ask before adding a surname.

- **"Mom" / "Mom's"** in a recipe title or filename = LeAnn. Existing entries: `chili-moms.md`, `chocolate-chip-cookies-moms.md`, `bread-honey-wheat-leann.md`, `cinnamon-rolls-leann.md`, `lasagna-moms.md`, `salsa-moms.md`, `pie-filling-moms-apple.md`. Some Drive docs say "LeAnn" and some say "Mom" for the same author.
- **"Grant" / "Grant's"** = Grant. He vibe-cooks, so his recipes were reconstructed by watching him: `burros-grants.md`, `chocolate-chip-cookies-grants.md`.
- **"Raquelle" / "Raquelle's"** = Colby's cousin. Existing entries: `stew-beef-raquelles.md` (her slow-cooker beef adaptation of a Ligurian veal stew). Came in via a recipes zip she shared, 2026-09-19.

## Importing from Bryce's Google Drive

Bryce owns the shared Google Drive `Recipes/` folder; the owner also has top-level `.gdoc` files in his own My Drive root. Syncing is on demand only, when the owner asks; there's no schedule.

**Last sync: 2026-05-17** — 25 recipes imported, Caribbean entrée folder carved out of curries. See `git log -- entrees/caribbean/ bread/bread-baguette-paul-hollywood.md` for the haul.

**Process**: read `.gdoc` files via the Drive MCP (`mcp__claude_ai_Google_Drive__read_file_content`). The `.gdoc` files in the filesystem are 178-byte JSON pointer files — they contain a `doc_id`, not content. Extract `doc_id` with `python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['doc_id'])" <file>` and feed to the MCP.

**Gotchas observed 2026-05-17:**

- **Some docs are images, not text.** `read_file_content` returns an empty string for these. Ask the user to open the doc and screenshot it, then `/check-screenshot`. (The 2026-05-17 moro de guandules recipe came in this way.)
- **Doc titles lie.** "CHUDS - Mississippi Pot Roast" was Alabama BBQ chicken; "Dominican Chicken 2 (pollo guisado)" was chicken soup (sopa de pollo). Always read the body before deciding category/filename.
- **Some "recipes" are just a YouTube URL.** Write a minimal link-only file in the matching category — see `entrees/american/chicken-leroy-and-lewis.md` for the format the user accepts.
- **AI-generated prose creeps in.** Flag doc bodies that read overly literary ("memory and mystery," nostalgic Nonna vignettes) before importing — may not be a real family recipe. On 2026-05-17 the user dropped a "Sunday Gravy" doc for this reason.
- **Drive's folder ≠ repo's folder.** Drive often files rice and brunch items under `/Entrees`. Apply this repo's categorization rules instead (Dominican rice → sides; biscuits-and-gravy → breakfast).
- **Triage strategy that worked**: pre-veto from filenames (most aren't wanted), then fetch only the keeps and skim for content quality. Batch-fetching everything is wasteful.

## Roadmap

Open items only; shipped work lives in the git history.

**Site (v1)** — recipes.skalchemy.com, time-boxed; close the milestone when v1 is live.

- **[#5 "Build recipes.skalchemy.com"](https://gitlab.com/colby.goettel/recipes/-/work_items/5)** (`Agent-ready`, `priority::weeks`) — v1 of the public site under `site/`: Markdown indexed at build time, recipe list, scaling, and cook mode, on the continuous-deploy pattern. Design decisions are in the issue's comments.
- **[#12 "Plan several recipes and get one merged shopping list"](https://gitlab.com/colby.goettel/recipes/-/work_items/12)** (`Agent-ready`, `priority::weeks`) — merged, grouped by store section, staples collapsed, "bought" kept separate from cook mode's "added", works offline.
- **[#13 "Bread view with baker's percentages and a theory page"](https://gitlab.com/colby.goettel/recipes/-/work_items/13)** (`Agent-ready`, `priority::weeks`) — flour is 100%, scale by dough weight, every ratio explained; needs the grams pass in #4.
- **[#14 "Private cook log and tested status"](https://gitlab.com/colby.goettel/recipes/-/work_items/14)** (`Agent-ready`, `priority::weeks`) — "made it" from cook mode, behind Cloudflare Access; doubles as the tested marker.
- **[#6 "Add front matter and normalize recipe structure for the site"](https://gitlab.com/colby.goettel/recipes/-/work_items/6)** (`Present`, `priority::months`) — YAML front matter (`status`, `serves`, `tags`) and one heading per section; blocked by #5's data model, lands after #4.
- **[#7 "Generate the README table of contents from front matter"](https://gitlab.com/colby.goettel/recipes/-/work_items/7)** (`Present`, `priority::months`) — the intro stays hand-written; the list becomes generated, alphabetical, and consistently cased.

**Maintenance** and **Creations**:

- **[#4 "Audit and sweep recipe units to the spelled-out house style"](https://gitlab.com/colby.goettel/recipes/-/work_items/4)** (`Agent-ready`, `priority::weeks`, milestone Maintenance) — audit every unit and fraction form in use, set a canonical spelling for each, then mechanically convert older recipes (`C`/`T`/`t` to `cup`/`tablespoon`/`teaspoon`, `1/2` to `½`) with a hand-reviewed diff.
- **[#9 "Give hot sauces their own folder"](https://gitlab.com/colby.goettel/recipes/-/work_items/9)** (`Present`, `priority::someday`, milestone Maintenance) — move the `sauce-*` hot sauces out of `salsas/`, if "hot sauce" is the right word for them.
- **[#10 "Move the Drive-import procedure into a project skill"](https://gitlab.com/colby.goettel/recipes/-/work_items/10)** (`Agent-ready`, `priority::someday`, milestone Maintenance) — keep `CLAUDE.md` about the repo; load the import steps only when importing.
- **[#11 "Rename Swedish pancakes v2 after what makes it different"](https://gitlab.com/colby.goettel/recipes/-/work_items/11)** (`Present`, `priority::someday`, milestone Maintenance).
- **[#3 "Cooking with tea: hōjicha and Kaga bōcha creations"](https://gitlab.com/colby.goettel/recipes/-/work_items/3)** (`Present`, `priority::months`, milestone Creations) — backlog of roasted-tea dishes beyond the bōcha curry and hōjicha panna cotta: lahpet (fermented tea-leaf salad), ochazuke, hōjicha salt, tea brine, tea smoking, sweets.
