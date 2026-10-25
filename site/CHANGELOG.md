# Changelog

The site's running version is the newest header here; CI bakes it into the image.

## v0.1.0 (2026-10-25)

- The public site: every recipe from the README, searchable, with scaling (½× to 3×) and cook mode (check off ingredients and steps; finished items collapse; the current step is highlighted; the screen stays awake).
- Ingredient lines are parsed into amount, unit and item when the image is built. Lines the parser can't read stay as written.
- Aggregate, cookie-free daily view and scale counts in Postgres.
