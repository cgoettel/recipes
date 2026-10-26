---
name: drive-import
description: Use when importing recipes from Google Drive into this repo — Bryce's shared Drive `Recipes/` folder or the owner's own `.gdoc` files ("sync the Drive recipes", "import from Bryce's Drive", "pull in that Google Doc recipe"). Covers reading `.gdoc` pointer files through the Drive MCP, triage, and the gotchas from past imports.
---

# Importing recipes from Google Drive

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

After importing, file each recipe the usual way (`CLAUDE.md`, "Adding a recipe"): the right folder, a kebab-case filename, front matter, and the house unit spellings, which CI checks. Update **Last sync** above when you're done.
