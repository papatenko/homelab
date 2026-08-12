# Backrest on the services host

This stack runs a Backrest instance on the services host and stores its repository configuration and runtime state under `BACKREST_DATA_DIR`.

The host root is mounted read-only at `/userdata` so the plan can cover host configuration, application bind mounts, Coolify state, and Docker named-volume data without granting Backrest write access to the host filesystem.

Configure a plan for the persistent paths that should be retained. Exclude rebuildable or intentionally disposable data, such as large model caches or generated media.

## Required stack variables

See `example.env` for safe defaults:

- `BACKREST_DATA_DIR`
- `BACKUP_SOURCE_PATH`
- `BACKREST_PORT`
- `TIMEZONE`

Use a separate repository path for this host rather than sharing a plan identity with another Backrest instance.
