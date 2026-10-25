# recipes site

The app behind [recipes.skalchemy.com](https://recipes.skalchemy.com): a public site over the Markdown recipes in this repo. FastAPI, Jinja, Tailwind v4, Postgres, on the smart-home k3s cluster like the other fleet apps.

The recipes stay plain Markdown at the top of the repo, and the README there stays the table of contents. The site reads both when the image is built, so a pushed recipe edit reaches the site in a few minutes with no other step.

## Layout

- `src/recipes_site/catalog.py`: reads `README.md` and every recipe file into records.
- `src/recipes_site/ingredients.py`: parses ingredient lines into amount, unit and item; scales and formats them.
- `src/recipes_site/app.py`: the routes. `/` is the list; `/<category>/<recipe>` is a recipe, mirroring the repo path.
- `src/recipes_site/static/app.js`: search, cook-mode check-offs (stored in the visitor's browser only), and the screen wake lock.
- `migrations/`: Alembic. The api pod's init container runs `alembic upgrade head`; `env.py` takes an advisory lock so two replicas can't race.

## Local development

```sh
cd site
uv sync --extra dev
npm ci && npm run build      # compiles static/output.css
RECIPES_AUTH_DISABLED=1 uv run uvicorn recipes_site.app:app --reload
uv run pytest
```

Without a database, pages still render; view counting logs a warning and moves on.
