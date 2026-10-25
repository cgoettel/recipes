# Changelog

The site's running version is the newest header here; CI bakes it into the image.

## v0.4.1 (2026-10-25)

- The stripes beside the wordmark link home, like the wordmark.
- Dropped the "lives as Markdown" footer note and the "View or edit the Markdown" link.

## v0.4.0 (2026-10-25)

- The owner's private cook log: "Made it" (with an optional note) at the end of any recipe, "made N times, last on…" or "untested" on each recipe, and a `/me` page with the log, the untested recipes, and the most viewed and most scaled. All of it sits behind Cloudflare Access and never shows to visitors.

## v0.3.0 (2026-10-25)

- Shopping list: "Add to shopping list" on any recipe (at its current scale), then `/list` merges every recipe you're making into one list grouped by store section, with staples collapsed at the bottom. Checking items off there is separate from cook mode. Your list lives only in your browser.
- Pages you've opened keep working without signal, through a small service worker.

## v0.2.0 (2026-10-25)

- Bread recipes show baker's percentages: each ingredient as a share of the flour, the hydration, salt, yeast, sugar and fat ratios with what each one means, and a "make a dough weighing" scaler.
- A theory page at `/learn/bakers-percentages`.
- Gram notes like `(≈240 g)` scale along with the amount.

## v0.1.0 (2026-10-25)

- The public site: every recipe from the README, searchable, with scaling (½× to 3×) and cook mode (check off ingredients and steps; finished items collapse; the current step is highlighted; the screen stays awake).
- Ingredient lines are parsed into amount, unit and item when the image is built. Lines the parser can't read stay as written.
- Aggregate, cookie-free daily view and scale counts in Postgres.
