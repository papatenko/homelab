# canvas-todoist

Syncs University of Houston Canvas assignments into Todoist every hour, using
the private Canvas Calendar Feed — no Canvas API token required.

Assignments land in a single **School** project with one label per course
(e.g. `@MATH-3321`). Each task carries the assignment link and description,
plus the due date. Due-date or title changes in Canvas update the task; tasks
you complete in Todoist are never recreated.

## Setup

1. Copy your **Canvas Calendar Feed URL**: log into
   [uh.instructure.com](https://uh.instructure.com), open **Calendar**, click
   **Calendar Feed** (bottom right), and copy the `.ics` link.
2. Copy your **Todoist API token**: Todoist → **Settings → Integrations →
   Developer**.
3. `cp example.env .env` and fill in both values.
4. Deploy: `make up SERVICE=canvas-todoist` (or via Portainer).

Sync state is kept in `./data/state.json` so re-runs never duplicate tasks.

## Manual testing

```sh
python sync.py --once --dry-run   # log planned changes without writing
python sync.py --once             # single real sync
```

## Limitations (ICS feed mode)

- No submission status in the feed, so tasks are **not** auto-completed when
  you submit in Canvas — check them off yourself.
- Assignments **without a due date** never appear in the feed and won't sync.
- Descriptions are plain text and may be truncated by Canvas.
- If you regenerate the Calendar Feed URL in Canvas, update `.env`.
