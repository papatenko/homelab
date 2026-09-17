# Headroom proxy

Persistent Headroom context-optimization proxy for coding-agent traffic. The
proxy is intentionally separate from OmniRoute: clients send requests to
Headroom first, and Headroom forwards them to the configured provider/backend.

## Upstream

- Documentation: https://headroomlabs-ai.github.io/headroom/docker-install/
- Source: https://github.com/headroomlabs-ai/headroom
- Image: `ghcr.io/headroomlabs-ai/headroom:code`
- Internal listener: `8989` in this deployment, matching the existing
  directory-scoped client convention. Upstream's default is `8787`.

## Portainer variables

Set these stack variables before deployment:

```env
DATA_DIR=/opt/stacks/headroom
HEADROOM_PORT=8989
HEADROOM_BIND_ADDRESS=127.0.0.1
HEADROOM_IMAGE=ghcr.io/headroomlabs-ai/headroom:code
HEADROOM_PROXY_TOKEN=<long random token, stored only in Portainer>
```

`DATA_DIR` is persistent Headroom state and must remain outside Portainer's Git
checkout. For a non-loopback binding, set `HEADROOM_PROXY_TOKEN` in Portainer
stack variables or the approved secret manager. Loopback-only deployments may
leave it empty. No provider credentials or agent
OAuth directories are mounted by this stack. Provider routing remains the
responsibility of the configured client backend or OmniRoute.

## Access boundary

The Services deployment publishes its port for private LAN/Tailscale clients
and requires `HEADROOM_PROXY_TOKEN`. The desktop-W​​SL deployment binds only to
loopback for local coding agents. It is not configured for Nginx Proxy Manager,
public DNS, Authentik, or internet exposure.

## Client integration

The client-side Headroom setting must use the same port as `HEADROOM_PORT`.
Directory-scoped routing is preferred over global shell variables. The
`headroom-add-directory` workflow creates shims for Claude, Codex, and OpenCode
and direct bypass commands for remote sessions.

The initial intended coding scope is the local `Nextcloud/Projects/code`
directory and its descendants on each developer machine, subject to each
machine's actual mount path. Existing `.envrc` and `.headroom-bin` files must
be inspected before applying changes. On the current Fedora setup, that scope
already uses `HEADROOM_PORT=8989`; before cutover, either expose this stack on
that same port or update the directory-scoped configuration atomically.

## Validation

```bash
docker compose -f headroom/docker-compose.yml config
git diff --check
curl -fsS http://<services-host>:8787/health
```

A running container is not sufficient. Verify the listener and a harmless
OpenAI-compatible request through the intended client route. Keep the direct
client commands available for rollback or remote-session compatibility.

## Rollback

Stop the Portainer stack and restore the prior client directory configuration.
Retain `${DATA_DIR:-/opt/stacks/headroom}` until the replacement path has been
validated and rollback is no longer needed. Do not delete it as part of normal
rollback.
