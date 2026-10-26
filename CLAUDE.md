# Recipes repo

Personal recipe collection in markdown. Each recipe is its own file under a category folder. The folders and each recipe's front matter are the catalog; the [README](README.md)'s recipe list is generated from them by CI.

## Working in this repo

- **GitLab is the home.** [colby.goettel/recipes](https://gitlab.com/colby.goettel/recipes) is canonical. GitHub ([cgoettel/recipes](https://github.com/cgoettel/recipes)) is a read-only mirror that CI force-pushes on every push to `main`, so anything merged on GitHub is overwritten. Issues and contributions go to GitLab.
- **Every change goes through a `git worktree`** — global rule, no exceptions (worktrees everywhere, every time). Branch off `origin/main` in a worktree, commit there, then merge to `main` and push; never edit or commit from the main checkout. **No MR is required** for recipe edits: commit, fast-forward `main`, and push. Changes under `site/` are the exception and go through an MR (see Operations). The worktree step is not optional.
- Conventional commit prefixes: `feat:` for new recipes, `fix:` for corrections, `refactor:` for reorganization, `docs:` for README-only changes.
- Issue housekeeping (milestones, labels) follows the fleet conventions in the `glab` skill. The `Maintenance`, `Creations` and `Site` milestones are evergreen buckets; never close them.
- **The repo is shared publicly, and that includes this file.** Recipe files and any markdown a cook would read should be written for a general audience — neutral voice, "you" or imperative form for instructions, no third-person asides about the owner. The README intro is the exception: it's the owner's own first-person voice, written and maintained by him, and it stays that way. Never put contact details (email addresses, phone numbers) for anyone in the repo, `CLAUDE.md` included. Personal context that shouldn't be public belongs in agent memory, not here.

## Operations

Git is the database for recipe text: rollback is `git revert`, and copies live on GitLab, GitHub, and every clone. The moving parts:

- **The site** ([recipes.skalchemy.com](https://recipes.skalchemy.com), app in `site/`, see [site/README.md](site/README.md)). Every push to `main`, recipe edits included, builds an image with the recipes baked in and tags it `main-<pipeline iid>-<sha>`. Flux image automation in smart-home deploys it to `recipes-dev` first; `verify_dev` waits for dev's `/health` to report the build, `promote` re-tags the same image `prod-<iid>-<sha>`, Flux commits that tag for prod (`kubernetes/recipes/app/values.yaml`), the api pod's init container runs the migrations, and `verify_live` goes green once the public `/health` reports it. CI runs on recipes' own in-cluster runner (smart-home `kubernetes/recipes-runner`). So a pushed recipe goes live in a few minutes with no other step, and a green pipeline means it's serving. Changes under `site/` go through an MR with green CI (`~/.claude/scripts/merge-mr`); recipe edits still go straight to `main`. `site_test` parses every recipe, so a recipe the parser can't read fails CI before it ships. The site follows the fleet conventions in the `unified-design` skill.
- **Rolling back.** The normal path is forward: `git revert` the bad commit here and push, and the pipeline ships the revert in a few minutes like any other change. Reverting the `chore(deploy)` commit in smart-home on its own does not stick, because Flux image automation puts the newest `prod-` tag back within a minute. When prod can't wait for a pipeline, run `flux suspend image update fleet` first (it pauses deploys for every fleet app, not just this one), revert the `chore(deploy)` commit, and run `flux resume image update fleet` once the fix's `prod-` tag exists. Neither path reverts a migration: if the older image can't run against the newer schema, roll forward instead.
- **Data and backups.** Postgres holds only the owner's cook log and daily view counts; recipe text never goes in the database. Prod is dumped hourly when it has changed, to deskf02 and Google Drive (smart-home `docs/backup-strategy.md`); `backup-now recipes` takes one on demand. Each night `dev-refresh` restores the newest prod dump into `recipes-dev`, which doubles as a restore test.
- **Dev and the edge.** `recipes-dev` has no public hostname. The only ways in are `kubectl` with the cluster kubeconfig and recipes' own CI jobs, through a NetworkPolicy keyed on this project's id; dev runs with sign-in turned off. At the edge, a route on the cluster's Cloudflare tunnel sends recipes.skalchemy.com to the app, and a Cloudflare Access app gates `/me`. Both were set through the Cloudflare API and live in Cloudflare, not in git; smart-home's `docs/runbooks/networking.md` records their settings. The Access app's audience tag is in the app's encrypted secret (`RECIPES_CF_ACCESS_AUDIENCE`), so recreating the Access app means updating that secret too.
- **CI** (`.gitlab-ci.yml`). `readme_toc` keeps the README's recipe list current (`site/src/recipes_site/toc.py`). On `main` it regenerates the list and commits any change back as "recipes CI", pushing with the `readme-bot` project access token in the masked, protected `README_BOT_TOKEN` variable. That push skips CI, since the site doesn't read the list. On any other branch the job only runs the generator to prove it works, so a branch's list can be stale until it reaches `main`. The token expires 2027-10-24: to rotate it, create a new project access token (`write_repository`, Maintainer) and replace the variable's value (#16 is the reminder). It is the only credential here that expires: the GitHub deploy key below, the runner token, the database passwords and the Access audience have no expiry. `mirror_to_github` runs after it and force-pushes `main` to GitHub, authenticating with the `GITHUB_DEPLOY_KEY` File-type CI variable, an SSH private key whose public half is a write-enabled deploy key on the GitHub repo. To rotate it: generate a new ed25519 key pair, replace the deploy key under the GitHub repo's Settings → Deploy keys (write access), and replace the private key in the `GITHUB_DEPLOY_KEY` variable (GitLab Settings → CI/CD → Variables, keeping it File type). The job re-adds the trailing newline glab strips. If the mirror job fails, `main` on GitLab is still fine; fix the key and re-run the job.
- **Formatting and secrets.** Locally, `mdformat --number` (with GFM and front matter plugins), whitespace fixers, gitleaks, and commitizen run from the owner's global pre-commit hook in dotfiles (`git/.config/git/hooks/pre-commit` and `git/.config/pre-commit/global.yaml`). CI checks the same things for commits made where that hook isn't installed: `check_format` runs the pinned mdformat from `.pre-commit-config.yaml` (on the `manual` stage, so it doesn't run twice locally; keep its versions in step with the global file), and `check_secrets` runs gitleaks over the full history. To fix a `check_format` failure, recommit the file through the global hook, which reformats it.

## Cook's preferences

Persistent preferences that should shape suggestions, edits, and new recipes across this repo.

**Philosophy.** Recipes are for remembering ingredients and proportions; technique and method are what actually matter. When writing or editing, lean toward describing *how* and *why* something is done, not just the sequence — method-level guidance is worth the line. The cook works by feel ("two spoonfuls," "half a jar," "quarter can"); recipes should give ranges rather than tweezer-precise grams unless chemistry demands it (bread, candy).

**One measure per ingredient.** Never write compound measures like "2 cups plus 1 teaspoon flour" or "⅔ stick (5⅔ tablespoons)". Round to the nearest amount a cook would actually measure (a whole tablespoon, a quarter stick, a common cup fraction). The only exception is when chemistry genuinely needs the precision, and then give grams instead.

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

1. Pick the right category folder (see structure below). The folder names become the README's and the site's section names.
2. Filename is kebab-case, no special characters. Examples: `chiles-gueros-rellenos-de-camaron.md`, `roast-chuck.md`.
3. File structure:
   - Optional YAML front matter (below).
   - `# Title` (H1).
   - Optional intro or attribution paragraph.
   - `## Ingredients`: a bulleted list, with `###` subheadings for parts ("### Crust", "### Filling").
   - `## Instructions`: a numbered list, with the same `###` parts. Write `1.` on every line if that's easier; the fleet-wide `mdformat --number` pre-commit hook renumbers ordered lists sequentially (1, 2, 3) on commit.
   - Optional `## Notes`, and any other sections a recipe needs (`## Equipment`, `## Serve with`).
4. Don't touch the README: CI adds the recipe to its list when it reaches `main` (see Operations, CI). On a branch the README list can lag; that's expected.
5. **Titles and headings are sentence case, per the Wikipedia style guide:** capitalize only the first word and proper nouns ("Almond bread", "Mom's chili", "Swedish pancakes (Åke Jon)"). Attributions are possessive ("Shirley's rolls"). Name the recipe after what someone would search for, and when a dish has two common names, put both in the title, for example "Dutch baby (German pancakes)".

### Front matter

All fields are optional:

```yaml
---
family: Pancakes # groups recipes under one label in the README and on the site
variant: Bacon cornmeal # what shows under that label
serves: 4 # or makes: 2 loaves; the site scales it
tags: [make-ahead]
---
```

- `family` and `variant` go together. A family with two or more recipes in a section shows as a label over its variants, and a family named after its section ("Bread" under Bread) lists just the variants. A recipe in no family lists under its title.

- `serves` or `makes`: the first number scales with the recipe ("6–8" at 2× reads "12–16").

- `tags`, from this vocabulary (`TAGS` in `catalog.py`; add a tag there when a recipe needs a new one, since CI rejects any tag that isn't listed):

  - Method: `grill`, `smoker`, `slow-cooker`, `instant-pot`, `no-cook`, `make-ahead`.
  - Diet: `vegetarian`, `vegan`.
  - Occasion: `thanksgiving`, `christmas`, `game-day`, `hot-dog-contest`.
  - Kind: `quick-bread`, `ferment`, `coffee`, `tea`.

  Tag diets conservatively, counting hidden sources: stock, fish sauce, gelatin, Miracle Whip, and any recipe a recipe links to (the classic lasagna isn't vegetarian because its red sauce has sausage). Diet tags are only on savory recipes, where they help.

- `aliases`: old paths a recipe used to live at, without `.md` (`aliases: [sauces-and-condiments/salsas/sauce-habanero]`). A recipe's path is its URL and the key for its cook-log history, so **renaming or moving a recipe means adding its old path here.** The site redirects the old URL and counts the old path's cook-log rows, views and saved shopping lists toward the new one. CI's renames guard (`site_test`, `recipes_site/renames.py`) fails any push that moves or deletes a recipe without one. To remove a recipe on purpose, alias it onto the recipe that replaces it, or list its old path in `site/retired-recipes.txt`.

What isn't a recipe: every `README.md`, `CLAUDE.md`, `contributing.md`, the root `staples.md` (the shopping list's staples, read by the site), `drinks/sodas/brew-day-notes/`, and everything under `site/` (`catalog.py`, `_NOT_RECIPES` and `_NOT_RECIPE_FILES`). Any other new Markdown file in a category folder shows up as a recipe.

## Directory structure

Folder names become the section names (dashes to spaces, first letter capitalized; `FOLDER_NAMES` in `catalog.py` holds the exceptions, "Entrées" and "East Asian"), so navigation maps 1:1 between filesystem, README, and site.

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
  hot-sauces/                     ← blended and squeezable; salsas are chunky and fresh
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
- **Salsa vs hot sauce.** A salsa is chunky and fresh. A hot sauce is blended smooth enough to squeeze from an old-school mustard bottle; the habanero sauce is about as chunky as a hot sauce gets. Hot sauces live in `sauces-and-condiments/hot-sauces/`; enchilada sauces are sauces.
- Single-item cuisine bins (e.g., `entrees/mediterranean/` is just chermoula lamb chops) are fine — they'll grow.

## Recipe formatting quirks

- **Units.** Every recipe uses these spellings (swept in #4). The parser still reads shorthand, but `site_test` fails CI on any ingredient line that uses it, naming the house spelling (`HOUSE_UNITS` in `ingredients.py`).

  | Unit                      | Write it as                                                                      |
  | ------------------------- | -------------------------------------------------------------------------------- |
  | Cup, tablespoon, teaspoon | `cup`/`cups`, `tablespoon(s)`, `teaspoon(s)`: never `C`, `T`, `t`, `tbsp`, `tsp` |
  | Ounce, pound              | `oz`, `lb` (no period, no `lbs`)                                                 |
  | Gallon, quart, pint       | `gallon(s)`, `quart(s)`, `pint(s)`                                               |
  | Package                   | `package(s)`                                                                     |
  | Butter (US)               | `¾ stick (6 tablespoons)`, `2 sticks (1 cup)`: under ¼ stick, tablespoons only   |
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

On demand only, when the owner asks. The procedure and its gotchas are in the `drive-import` project skill (`.claude/skills/drive-import/SKILL.md`); load it before importing.

## Roadmap

Open items only; shipped work lives in the git history.

**Site** (from the #15 handover, in priority order):

- **[#20 ""I have…" ingredient search"](https://gitlab.com/colby.goettel/recipes/-/work_items/20)** (`Present`, `priority::months`) — what else uses the leftover leek; mock first.
- **[#24 "Count recipes added to shopping lists"](https://gitlab.com/colby.goettel/recipes/-/work_items/24)** (`Agent-ready`) and **[#25 "Tap-to-start timers on recipe steps"](https://gitlab.com/colby.goettel/recipes/-/work_items/25)** (`Present`, mock first), both `priority::someday`.
- Cluster side, in smart-home: [#291 "Uptime probe and Discord alert channel for recipes"](https://gitlab.com/colby.goettel/smart-home/-/work_items/291), [#292 "Restore and database password rotation runbook for recipes (and the fleet)"](https://gitlab.com/colby.goettel/smart-home/-/work_items/292), [#293 "Alert on stalled Flux image automation and offline GitLab runners"](https://gitlab.com/colby.goettel/smart-home/-/work_items/293).

**Maintenance** and **Creations**:

- **[#16 "Rotate the README bot token before it expires"](https://gitlab.com/colby.goettel/recipes/-/work_items/16)** (`Agent-ready`, `priority::someday`, milestone Maintenance, due 2027-10-19) — the `readme-bot` token CI uses to commit the generated README list expires 2027-10-24.
- **[#3 "Cooking with tea: hōjicha and Kaga bōcha creations"](https://gitlab.com/colby.goettel/recipes/-/work_items/3)** (`Present`, `priority::months`, milestone Creations) — backlog of roasted-tea dishes beyond the bōcha curry and hōjicha panna cotta: lahpet (fermented tea-leaf salad), ochazuke, hōjicha salt, tea brine, tea smoking, sweets.
