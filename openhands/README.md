# OpenHands

OpenHands Agent Canvas provides a browser UI for connecting to OpenHands agent servers and project workspaces.

## Upstream

- Repository: https://github.com/OpenHands/OpenHands
- Docker guidance: https://github.com/OpenHands/OpenHands#option-2-with-a-docker-sandbox
- Image: `ghcr.io/openhands/agent-canvas:1.18.0`

## Recommended placement

Recommended host: Services host, after the current migration observation window.

Reasons:

- Keeps the UI beside the existing Coolify and AI services.
- Uses a dedicated published port, `8011`, because Services already uses port `8000` for Coolify.
- Keeps OpenHands state and project workspaces on stable host paths.

Tradeoff: OpenHands is an agent control surface. Do not expose it publicly or mount broad host paths without a deliberate security review.

## Portainer deployment

Create a Git-backed Portainer Stack from:

- Stack name: `openhands`
- Repository: `https://github.com/papatenko/homelab.git`
- Reference: `refs/heads/main`
- Compose path: `openhands/docker-compose.yml`

Required stack variables:

- `DATA_DIR`, default `/opt/stacks/openhands`
- `PROJECTS_DIR`, default `/opt/stacks/openhands/projects`
- `COMPOSE_PORT_HTTP`, default `8011`
- Optional `OPENHANDS_IMAGE`, default `ghcr.io/openhands/agent-canvas:1.18.0`

The image listens on port `8000` internally and is published on `8011` by default. The persistent OpenHands configuration is mounted at `/home/openhands/.openhands`; project workspaces are mounted at `/projects`.

Create the host directories before deployment and populate `/projects` only with repositories that OpenHands is explicitly allowed to access. Do not mount `/`, `/root`, Docker socket, or unrelated secrets.

## Initial setup

1. Deploy the stack through Portainer after this change is merged.
2. Open `http://<services-host>:8011/canvas` from the LAN.
3. Configure an approved OpenHands Agent Server/backend in the UI.
4. Confirm the selected backend can access only the intended project workspace.
5. Keep the service LAN-only until authentication and the agent backend have been tested.

## Validation

```bash
docker compose -f openhands/docker-compose.yml config
curl -fsS http://<services-host>:8011/canvas
```

Homepage registration is included in `homepage/config/services.yaml` using the existing `HOMEPAGE_VAR_COOLIFY_IP` runtime variable. No Portainer deployment or public proxy exposure is performed by this repository change.
