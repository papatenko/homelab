# n8n

Self-hosted n8n workflow automation stack for Portainer Git deployment.

## Compose source

- Official image: `docker.n8n.io/n8nio/n8n:stable`
- Upstream docs: https://docs.n8n.io/deploy/host-n8n/install-options/use-a-cloud-provider/use-docker-compose
- Health endpoints: https://docs.n8n.io/deploy/host-n8n/keep-n8n-running/monitor-n8n

This repo intentionally does not include Traefik from the upstream example. Use the existing reverse-proxy layer if n8n needs HTTPS access.

## Required Portainer variables

Copy `example.env` into the Portainer stack environment and set at minimum:

- `DATA_DIR` — persistent data root for n8n state and workflow files.
- `N8N_ENCRYPTION_KEY` — generate once and keep it stable; n8n uses it to encrypt credentials.

## Exposure notes

- Direct LAN default: `http://<host>:5678`
- If exposed through an HTTPS reverse proxy, update:
  - `N8N_PROTOCOL=https`
  - `N8N_HOST=<n8n hostname>`
  - `N8N_EDITOR_BASE_URL=https://<n8n hostname>`
  - `N8N_WEBHOOK_URL=https://<n8n hostname>/`
  - `N8N_SECURE_COOKIE=true`

Do not commit the real encryption key or hostname-specific secrets.
