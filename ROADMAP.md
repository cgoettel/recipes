# recipes — roadmap

Open work only; shipped work lives in the git history, never here. Priority labels
(`priority::next` > `weeks` > `months` > `someday`) are the source of truth. This file
adds the lane each issue sits in. **Agent-ready** means executable in an unattended
session. Rules and conventions live in [`CLAUDE.md`](CLAUDE.md).

## Agent-ready

- **[#26 "Add README badges"](https://gitlab.com/colby.goettel/recipes/-/work_items/26)**
  (`priority::weeks`, milestone Maintenance) — pipeline status, the live site version,
  a recipe count fed by `readme_toc`, and a "free to share" badge for the LICENSE note.
- **[#16 "Rotate the README bot token before it expires"](https://gitlab.com/colby.goettel/recipes/-/work_items/16)**
  (`priority::someday`, milestone Maintenance, due 2027-10-19) — the `readme-bot` token
  CI uses to commit the generated README list expires 2027-10-24.

## Tracked in smart-home

The site's cluster side, from the #15 handover, in priority order:

- [#291 "Uptime probe and Discord alert channel for recipes"](https://gitlab.com/colby.goettel/smart-home/-/work_items/291)
  (`Present`, `priority::weeks`)
- [#292 "Restore and database password rotation runbook for recipes (and the fleet)"](https://gitlab.com/colby.goettel/smart-home/-/work_items/292)
  (`Agent-ready`, `priority::months`)
- [#293 "Alert on stalled Flux image automation and offline GitLab runners"](https://gitlab.com/colby.goettel/smart-home/-/work_items/293)
  (`Present`, `priority::someday`)
