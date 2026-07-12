# Actual Budget

Self-hosted Actual Budget server with an optional HTTP/SSE Actual MCP companion for agent access.

## Upstream sources

- Actual Budget server: https://actualbudget.org/docs/install/docker/
- Actual server image: `docker.io/actualbudget/actual-server:latest`
- Actual MCP project: https://github.com/s-stefanov/actual-mcp
- Actual MCP image: `sstefanov/actual-mcp:latest`

`sstefanov/actual-mcp:latest` publishes `linux/amd64` and `linux/arm64` images.

## What it runs

- `actual_server`
  - Web UI/API port: `5006`
  - Data path: `${ACTUAL_DATA_DIR:-/opt/stacks/actual/data}` mounted at `/data`
- `actual_mcp`
  - HTTP/Streamable MCP and legacy SSE port: `3000`
  - Scratch/data path: `${ACTUAL_MCP_DATA_DIR:-/opt/stacks/actual-mcp/data}` mounted at `/data`
  - Default MCP endpoint: `http://<host>:3000/mcp`
  - Legacy SSE endpoint: `http://<host>:3000/sse`

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

The MCP container starts with `--sse --enable-bearer`. It does **not** enable write tools by default. If write access is desired later, add `--enable-write` to the service command after confirming the risk.

## Persistent data

Persistent state lives outside Portainer's Git checkout:

```text
/opt/stacks/actual/data
/opt/stacks/actual-mcp/data
```

## Nginx Proxy Manager

Actual can be exposed through NPM by proxying to the Docker host on `ACTUAL_PORT`.

Actual MCP should normally stay private. If it is exposed beyond the LAN, keep bearer authentication enabled and put it behind HTTPS. MCP access can read sensitive financial data; do not expose it without a strong token and a clear reason.

## Authentik

Actual has its own authentication model. Use Authentik/NPM forward-auth only if you intentionally want an additional gate in front of the web UI or MCP endpoint.

## API key / agent access

For Hermes MCP usage, configure Hermes as a remote HTTP MCP server pointing at the MCP endpoint and pass the bearer token as an authorization header. Store the bearer token outside Git, for example in `pass` under `mcp/actual-budget/bearer-token`.

## Validation

After deployment:

1. Verify `actual_server` is healthy.
2. Open Actual on port `5006` and complete/login to the app.
3. Verify `actual_mcp` is running.
4. Confirm `GET /mcp` or `/sse` without a bearer token is rejected.
5. Test MCP with a bearer token from the intended client.
6. Confirm data is stored under `/opt/stacks/actual` and `/opt/stacks/actual-mcp`.

## Rollback

If deployment fails:

1. Stop/remove the Portainer stack or remove only the `actual_mcp` service if Actual itself is healthy.
2. Remove any dedicated NPM proxy host, if created.
3. Remove any dedicated Authentik app/provider, if created.
4. Preserve `/opt/stacks/actual` unless Justin confirms the data can be deleted.
