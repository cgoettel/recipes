# Changelog

The site's running version is the newest header here; CI bakes it into the image.

## v0.8.3 (2026-10-25)

- Hardening (#18): a dough target like `inf` no longer crashes a bread page; the cook log pages show a plain "not right now" page when the database is down instead of an error; the private-page check also verifies who issued the sign-in and ignores email case; the app refuses to start with sign-in turned off when it has prod's full Access config; cook-log dates default to UTC like the counts; CI images are pinned.

## v0.8.2 (2026-10-25)

- `/health` fails (503) when the recipe catalog can't load, so a build with an unreadable recipe never goes live: the old pods keep serving and the pipeline goes red instead of green (#17).

## v0.8.1 (2026-10-25)

- Nearly every recipe now says how much it serves or makes: 155 more, estimated from their quantities and pans.
- Scaling a yield only touches the amount it leads with, so "one 9x13 pan" reads "one 9x13 pan × 2", not "one 18x13 pan". Measured yields scale like ingredients ("about ¾ cups" at ½×).

## v0.8.0 (2026-10-25)

- The site reads recipes straight from their folders and front matter, not from the README. The README's recipe list is now generated from the same data, by CI.
- Recipes can say how much they make: "Serves 6–8" or "Makes 2 loaves" shows under the title and scales with the recipe.
- Tags show as chips on each recipe and open the index filtered to that tag (`/?q=grill`).
- Recipe families come from front matter (`family` and `variant`), so titles read naturally ("Almond bread") while the index still groups them.

## v0.7.2 (2026-10-25)

- The menu opens over the page instead of pushing it down.
- The person dropdown drops its "Dark mode" label and shrinks to fit the switch and the cook log link.

## v0.7.1 (2026-10-25)

- The person button opens a dropdown over the page, like the settings gear in the other fleet apps: a dark-mode switch (🌻 / 🌘) and the cook log link.

## v0.7.0 (2026-10-25)

- A new header: a cart for the shopping list, a menu (all recipes, the shopping list, baker's percentages, and the categories), and a person button for day or night and the cook log.
- The person button shows 👩🏻‍🦳 when the owner's login is current and a plain outline otherwise, so an expired login is visible at a glance.
- Anyone else who reaches `/me` gets a plain "this page is private" page.

## v0.6.0 (2026-10-25)

- Butter reads in sticks, with tablespoons alongside: "¾ stick (6 tablespoons) butter". Scaling keeps both in step, shows cups from two sticks up, and drops to tablespoons when the amount isn't a quarter stick. Cinnamon sticks are still just counted.

## v0.5.0 (2026-10-25)

- Tapping a step marks your place: it finishes every step before it and reopens every step after it. Recipes with separate parts (dough and filling, cake and icing) track each part on its own.
- The header and footer stripes change on every page, with no color repeated on a page.
- The index groups recipe families: "Pancakes" shows once over Classic, Whole Wheat and the rest, and a section no longer repeats its own name ("Bread — Almond" under Bread is just "Almond").

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
