# Uptime Kuma

This is a Git-backed Compose definition for private uptime monitoring. It is intentionally
LAN/VPN-only by default and does not configure public DNS, reverse proxy, identity, or alert
credentials.

## Upstream and image

- Documentation: <https://github.com/louislam/uptime-kuma/wiki/%F0%9F%94%A7-How-to-Install>
- Docker image documentation: <https://github.com/louislam/uptime-kuma>
- Image: `louislam/uptime-kuma:2.5.3` (official release; Uptime Kuma publishes multi-architecture images including ARM64)

The release tag is pinned for reproducibility. Confirm the upstream release and manifest before
updating it on a Raspberry Pi.

## Secure, durable defaults

- Uptime Kuma's SQLite/application state is stored in the local bind mount
  `${KUMA_DATA_DIR:-/opt/stacks/uptime-kuma}` at `/app/data`. Do not place this high-churn state
  on NAS/NFS.
- The port binds to `${KUMA_BIND_ADDRESS:-127.0.0.1}` by default. The coordinator may select a
  private LAN/VPN interface for approved clients; never publish it on a public interface without
  a separately reviewed access-control design.
- No Docker socket is mounted. Monitoring should use HTTP/TCP/DNS probes and approved agents;
  socket access requires a separate security review and explicit approval.
- No secrets are present in this repository.

## Coordinator-only runtime setup

The coordinator creates the local data directory, supplies non-secret stack variables through the
approved Git-backed control plane, and completes first-run setup in the Kuma UI. Before rendering
or deploying, run the repository preflight on the target host with the exact deployment values:

```bash
KUMA_BIND_ADDRESS=<approved-private-address> \
KUMA_PORT=<approved-port> \
KUMA_DATA_DIR=<local-directory> \
./uptime-kuma/preflight.sh
```

The preflight rejects unspecified/public bindings, non-local storage, and missing or unwritable
data directories. After deployment, require the strict upstream-compatible HTTP 302 container
healthcheck to become healthy. Workers must not deploy remotely or create monitor credentials.
Configure monitors from the approved monitoring matrix only, and keep existing n8n watchlist
coverage until parity and alert behavior are verified.

When ntfy is selected as an alert channel, add the authenticated read/write details through the
Kuma UI or approved secret mechanism at runtime; never commit them or place them in Compose.

## Validation

```bash
docker compose -f uptime-kuma/compose.yaml --env-file uptime-kuma/.env.example config
```

This only renders configuration; deployment and first-run setup are intentionally out of scope.

## Backup and rollback

Back up the local data directory with the existing host backup policy, including SQLite files.
For rollback, stop the stack, restore the previous Git revision and preserved data directory, then
verify monitor definitions and notification settings before resuming checks.
