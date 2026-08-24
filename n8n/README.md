# n8n

Self-hosted n8n workflow automation with PostgreSQL and the n8n AI Assistant sandbox, deployed as a Portainer Git stack.

## Compose source

- n8n image: `docker.n8n.io/n8nio/n8n:stable`
- PostgreSQL image: `postgres:16-alpine`
- AI Assistant sandbox images: `ghcr.io/n8n-io/n8n-sandbox-service-*` (pinned versions)
- Upstream n8n Docker Compose guide: https://docs.n8n.io/deploy/host-n8n/install-options/install-using-docker-compose
- AI Assistant configuration: https://docs.n8n.io/deploy/host-n8n/configure-n8n/set-up-ai-assistant
- Monitoring endpoints: https://docs.n8n.io/hosting/configuration/configuration-examples/monitoring/

This stack intentionally does not include Traefik. Add reverse-proxy, TLS, and public-webhook settings only after a separate approval.

`n8n-init` initializes the two n8n-owned bind mounts with the container's non-root UID, so a fresh Portainer deployment can write its configuration and workflow files without manual host-side ownership changes.

## AI Assistant architecture

The default stack includes n8n's self-hosted sandbox:

- `sandbox-certs` generates the internal mTLS certificates and exits.
- `sandbox-api` is the private control plane that n8n contacts.
- `sandbox-runner-1` runs the actual code sandboxes through Docker-in-Docker.

The runner is `privileged: true`, which is a significant security boundary. It has no published ports and must remain on the private Compose network. Treat this setup as appropriate for a controlled homelab or evaluation environment. n8n currently recommends Daytona for production deployments.

## SearXNG status

SearXNG is enabled by default for the n8n AI Assistant. Set a unique `SEARXNG_SECRET` in Portainer, generated for example with `openssl rand -hex 32`. The stack fails closed if the secret is missing. n8n uses the internal URL `http://searxng:8080`, and no SearXNG port is published to the host.

The SearXNG configuration is stored in `searxng-settings.yml` and enables the JSON API required by n8n. Do not publish its port.

## Required Portainer variables

Copy `example.env` into the Portainer stack environment and set at minimum:

- `DATA_DIR` — persistent root for n8n data, PostgreSQL, workflow files, and local backups.
- `POSTGRES_PASSWORD` — a unique non-empty PostgreSQL password.
- `N8N_ENCRYPTION_KEY` — generate once and retain permanently; n8n uses it to encrypt credentials.
- `SANDBOX_API_KEYS` — sandbox API key list.
- `SANDBOX_API_RUNNER_REGISTRATION_TOKEN` — runner registration token.
- `SANDBOX_API_RUNNER_API_KEY` — runner authentication key.
- `N8N_INSTANCE_AI_SANDBOX_API_KEY` — must match a value in `SANDBOX_API_KEYS`.
- Configure the AI model and provider key in the n8n UI. Do not set `N8N_INSTANCE_AI_MODEL` in Portainer if the model should remain editable from the UI, because n8n treats that value as environment-managed.

Do not commit real passwords, encryption keys, model keys, sandbox tokens, or hostname-specific settings. Retrieve service credentials through the approved secret-delivery path.

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
- `sandbox-api` uses `http://sandbox-api:8080/healthz` internally.

Useful verification commands after deployment:

```bash
docker compose exec n8n wget -qO- http://sandbox-api:8080/healthz
curl -sf http://localhost:5678/healthz
```

`sandbox-certs` must complete successfully and `sandbox-api` must become healthy before n8n starts. The runner registers asynchronously after the API starts, so verify runner registration in the `sandbox-api` logs before testing an AI Assistant code execution.

## Rollback

To disable AI Assistant without deleting n8n data, revert the Compose change and redeploy the previous Git revision. Preserve the PostgreSQL data, n8n data, encryption key, and `n8n-sandbox-tls` volume until the replacement stack is healthy. Removing the sandbox services should not remove workflows or credentials.
