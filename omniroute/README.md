# OmniRoute

Self-hosted AI gateway that exposes one OpenAI-compatible endpoint backed by 290+ LLM
providers (90+ with free tiers), with a web dashboard, request compression, and
MCP/A2A support.

## What it runs

- Upstream: https://github.com/diegosouzapw/OmniRoute
- Image: `diegosouzapw/omniroute` (Docker Hub: https://hub.docker.com/r/diegosouzapw/omniroute)
- Internal HTTP port: `20128` (dashboard + API, single-port mode by default)
- Persistent data (SQLite DB, logs, backups): `${DATA_DIR:-/opt/stacks/omniroute}/data`
- OpenAI-compatible base URL once deployed: `http://<host>:20128/v1`

## Portainer variables

Copy `example.env` into Portainer stack environment variables and set at minimum:

```env
DATA_DIR=/opt/stacks/omniroute
OMNIROUTE_IMAGE=diegosouzapw/omniroute:3.8.49
COMPOSE_PORT_HTTP=20128
JWT_SECRET=<openssl rand -base64 48>
API_KEY_SECRET=<openssl rand -hex 32>
INITIAL_PASSWORD=<a real password, not CHANGEME>
STORAGE_ENCRYPTION_KEY=<openssl rand -hex 32, optional>
```

`JWT_SECRET` and `API_KEY_SECRET` are required before first run — the container signs
session cookies and encrypts stored provider API keys with them. Generate both once and
retain them permanently; rotating `API_KEY_SECRET` invalidates previously stored provider
keys.

## Remote access

Publish only the HTTP port internally, then expose it through your reverse proxy for
HTTPS remote access. Do not expose the dashboard directly to the public internet without
a reverse proxy in front of it, since `INITIAL_PASSWORD` is the only gate until you log
in and change it.

## First-run

1. Deploy the stack and open `http://<host>:${COMPOSE_PORT_HTTP}`.
2. Log in with `INITIAL_PASSWORD`, then change it under Dashboard -> Settings -> Security.
3. Add provider API keys (or rely on OmniRoute's built-in free-tier provider pool) from
   the dashboard.
4. Point OpenAI-compatible clients at `http://<host>:20128/v1` with a bearer token issued
   from the dashboard.

## Validation and rollback

- `docker compose -f omniroute/docker-compose.yml config` to validate the compose file.
- If the deployment is abandoned, remove the Portainer stack and the
  `${DATA_DIR:-/opt/stacks/omniroute}` host data path only after explicit confirmation.
