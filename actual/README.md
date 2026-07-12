# Actual Budget

Self-hosted Actual Budget server with an optional HTTP Actual MCP companion for agent access.

## Upstream sources

- Actual Budget server: https://actualbudget.org/docs/install/docker/
- Actual server image: `docker.io/actualbudget/actual-server:latest`
- Actual MCP project: https://github.com/agigante80/actual-mcp-server
- Actual MCP image: `ghcr.io/agigante80/actual-mcp-server:latest`

The maintained Actual MCP image publishes multi-architecture container images and tracks newer Actual Budget API migrations more closely than older community images.

## What it runs

- `actual_server`
  - Web UI/API port: `5006`
  - Data path: `${ACTUAL_DATA_DIR:-/opt/stacks/actual/data}` mounted at `/data`
- `actual_mcp`
  - HTTP MCP port: `3600`
  - Scratch/data path: `${ACTUAL_MCP_DATA_DIR:-/opt/stacks/actual-mcp/data}` mounted at `/app/data`
  - MCP endpoint: `http://<host>:3600/http`
  - Health endpoint: `http://<host>:3600/health`

## Portainer variables

Copy `example.env` into Portainer stack variables and fill the secret values outside Git.

Required for Actual MCP:

```env
ACTUAL_MCP_ACTUAL_PASSWORD=<actual-server-password>
ACTUAL_MCP_BUDGET_SYNC_ID=<budget-sync-id>
ACTUAL_MCP_BEARER_TOKEN=<long-random-token>
```

Optional:

```env
ACTUAL_MCP_BUDGET_ENCRYPTION_PASSWORD=<budget-unlock-password-if-different>
```

The MCP container uses static bearer authentication through `MCP_SSE_AUTHORIZATION`, populated from `ACTUAL_MCP_BEARER_TOKEN`. Keep the token outside Git.

## Persistent data

Persistent state lives outside Portainer's Git checkout:

```text
/opt/stacks/actual/data
/opt/stacks/actual-mcp/data
```

The MCP data directory is required because Actual's API library downloads a local copy of the budget before querying or syncing.

## Nginx Proxy Manager

Actual can be exposed through NPM by proxying to the Docker host on `ACTUAL_PORT`.

Actual MCP should normally stay private. If it is exposed beyond the LAN, keep bearer authentication enabled and put it behind HTTPS. MCP access can read sensitive financial data; do not expose it without a strong token and a clear reason.

## Authentik

Actual has its own authentication model. Use Authentik/NPM forward-auth only if you intentionally want an additional gate in front of the web UI or MCP endpoint.

The maintained MCP image also supports OIDC/JWKS validation, but static bearer auth is simpler for a single agent client.

## API key / agent access

For Hermes MCP usage, configure Hermes as a remote HTTP MCP server pointing at `http://<host>:3600/http` and pass the bearer token as an authorization header. Store the bearer token outside Git, for example in `pass` under `mcp/actual-budget/bearer-token`.

## Validation

After deployment:

1. Verify `actual_server` is healthy.
2. Open Actual on port `5006` and complete/login to the app.
3. Verify `actual_mcp` is running.
4. Confirm `GET /health` returns an OK status.
5. Confirm an MCP initialize request to `/http` without a bearer token is rejected.
6. Test MCP initialize/tool discovery with a bearer token from the intended client.
7. Call a low-risk data tool, such as account listing, to confirm Actual API/budget migrations are compatible.
8. Confirm data is stored under `/opt/stacks/actual` and `/opt/stacks/actual-mcp`.

## Rollback

If deployment fails:

1. Stop/remove the Portainer stack or remove only the `actual_mcp` service if Actual itself is healthy.
2. Remove any dedicated NPM proxy host, if created.
3. Remove any dedicated Authentik app/provider, if created.
4. Preserve `/opt/stacks/actual` unless Justin confirms the data can be deleted.
