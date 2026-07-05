# Authentik

Docker Compose stack for Authentik.

## Required environment variables

Set these in your deployment environment; do not commit real secret values.

```env
PG_PASS=<generate a strong password>
AUTHENTIK_SECRET_KEY=<generate a strong secret>
```

Optional overrides:

```env
DATA_DIR=/path/to/persistent/data
COMPOSE_PORT_HTTP=9000
```

## Reverse proxy

If exposing Authentik behind a reverse proxy, forward HTTP traffic to the host and port published by `COMPOSE_PORT_HTTP`.

Enable websocket support and TLS at the proxy if your proxy supports those options.

## Docker socket note

The upstream Authentik Compose file can mount `/var/run/docker.sock` into the worker so Authentik can automatically manage Docker outposts. This stack does **not** mount the socket by default because that gives the worker broad control over the Docker host. If Docker outposts are needed later, prefer adding a Docker socket proxy or deploying the outpost manually.

## Initial setup

After the stack is running and reachable through your chosen hostname, visit:

```text
https://<your-authentik-hostname>/if/flow/initial-setup/
```

Set the password for the default `akadmin` user.
