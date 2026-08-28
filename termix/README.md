# Termix

Termix is a self-hosted server-management interface with browser-based SSH terminals, SFTP file management, tunnels, host metrics, and optional remote desktop support.

## Upstream

- Repository: <https://github.com/Termix-SSH/Termix>
- Docker deployment guidance: <https://github.com/Termix-SSH/Termix#docker>
- Security advisories: <https://github.com/Termix-SSH/Termix/security/advisories>

## Stack

This stack runs the SSH/SFTP portion of Termix with SQLite-backed application data. Remote desktop support is intentionally omitted, so the optional `guacd` service is not deployed.

- Networking: `network_mode: host` — required so Termix's Wake-on-LAN feature can actually broadcast magic packets onto the LAN (Docker's default bridge network drops broadcast traffic before it reaches the physical NIC; same fix already applied to `upsnap`, see `upsnap/docker-compose.yml`)
- Port: `8080` (bound directly on the host; no port mapping under host networking)
- Persistent mount: `${DATA_DIR}/` to `/app/data`
- Telemetry: disabled by default
- Image: `ghcr.io/lukegus/termix:latest` (official multi-architecture image, including arm64)

Set the stack variables from `example.env` in Portainer. Do not commit real credentials or application data.

## First run

1. Open Termix on host port `8080`.
2. Complete the initial administrator setup.
3. Add SSH hosts and credentials through Termix.
4. Keep the application reachable only through the intended LAN/VPN or authenticated reverse-proxy path.

## Validation

```bash
docker compose -f termix/docker-compose.yml config
```

After deployment, verify the container is running, `/opt/stacks/termix` (or the configured `DATA_DIR`) is mounted as `/app/data`, and the Termix web interface responds on the configured host port.

## Rollback

Redeploy the previous Git revision through Portainer. Preserve the Termix data directory until the replacement has been verified or the service is intentionally retired.
