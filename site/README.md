# recipes site

The app behind [recipes.skalchemy.com](https://recipes.skalchemy.com): a public site over the Markdown recipes in this repo. FastAPI, Jinja, Tailwind v4, Postgres, on the smart-home k3s cluster like the other fleet apps.

The recipes stay plain Markdown at the top of the repo. The site reads the folders and each recipe's front matter when the image is built (and generates the README's recipe list from the same data), so a pushed recipe edit reaches the site in a few minutes with no other step.

Postgres holds only the owner's cook log (`/me`, behind Cloudflare Access) and daily view and scale counts. Visitors' check-offs and shopping plans stay in their own browser. Deploys, rollback, backups and the edge setup are in the repo's [CLAUDE.md](../CLAUDE.md), under Operations.

## Layout

- `src/recipes_site/catalog.py`: reads the recipe folders and each recipe's front matter into records (plus the README intro, as the house notes, and the root `staples.md`, the shopping list's staples).
- `src/recipes_site/toc.py`: generates the README's recipe list from the same data; CI runs it.
- `src/recipes_site/renames.py`: the CI guard that fails a moved or deleted recipe left without an `aliases` entry (or a line in `retired-recipes.txt`).
- `src/recipes_site/ingredients.py`: parses ingredient lines into amount, unit and item; scales and formats them.
- `src/recipes_site/app.py`: the routes. `/` is the list; `/<category>/<recipe>` is a recipe, mirroring the repo path.
- `src/recipes_site/static/app.js`: search, cook-mode check-offs and shopping plans (stored in the visitor's browser only), and the screen wake lock.
- `migrations/`: Alembic. The api pod's init container runs `alembic upgrade head`; `env.py` takes an advisory lock so two replicas can't race.

## Local development

```sh
cd site
uv sync --extra dev
npm ci && npm run build      # compiles static/output.css, copies static/htmx.min.js
RECIPES_AUTH_DISABLED=1 uv run uvicorn recipes_site.app:app --reload
uv run pytest
```

Without a database, pages still render; view counting logs a warning and moves on.
