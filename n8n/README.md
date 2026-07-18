# n8n

Self-hosted n8n workflow automation with PostgreSQL, deployed as a Portainer Git stack.

## Compose source

- n8n image: `docker.n8n.io/n8nio/n8n:stable`
- PostgreSQL image: `postgres:16-alpine`
- Upstream n8n Docker Compose guide: https://docs.n8n.io/hosting/installation/docker/
- Monitoring endpoints: https://docs.n8n.io/hosting/configuration/configuration-examples/monitoring/

This stack intentionally does not include Traefik. Add reverse-proxy, TLS, and public-webhook settings only after a separate approval.

## Required Portainer variables

Copy `example.env` into the Portainer stack environment and set at minimum:

- `DATA_DIR` — persistent root for n8n data, PostgreSQL, workflow files, and local backups.
- `POSTGRES_PASSWORD` — a unique non-empty PostgreSQL password.
- `N8N_ENCRYPTION_KEY` — generate once and retain permanently; n8n uses it to encrypt credentials.

Do not commit real passwords, encryption keys, or hostname-specific settings.

## Exposure

The default is direct LAN HTTP on port 5678. For this mode:

- `N8N_PROTOCOL=http`
- `N8N_SECURE_COOKIE=false`
- Set `N8N_HOST`, `N8N_EDITOR_BASE_URL`, and `N8N_WEBHOOK_URL` in Portainer to the approved LAN address.

If access later moves behind an HTTPS reverse proxy, set the protocol, host, editor base URL, and webhook URL to the approved HTTPS hostname, then set `N8N_SECURE_COOKIE=true`.

## Local PostgreSQL backups

`backup-postgres.sh` creates a PostgreSQL custom-format dump in `${DATA_DIR}/backups/postgres`, validates it with `pg_restore --list`, and removes dumps older than 14 days by default.

Install a copy on the Docker host outside Portainer's Git checkout, then run it there:

```bash
chmod 700 /opt/stacks/n8n/bin/backup-postgres.sh
/opt/stacks/n8n/bin/backup-postgres.sh
```

Schedule it only after the first manual backup succeeds. The local backup directory is not off-host protection; replicate it to an approved backup target before relying on n8n for important credentials or workflows.

## Health checks

- `/healthz` confirms the n8n web service is reachable.
- `/healthz/readiness` additionally checks database connectivity and migrations; Docker uses this for the container healthcheck.
