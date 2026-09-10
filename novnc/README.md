# noVNC browser desktop

A private, self-contained noVNC browser desktop for temporary interactive browser workflows. It follows the configuration qualified on Hermes: Xvfb, Fluxbox, x11vnc, websockify, noVNC, and Chromium in one container.

This stack is intentionally separate from NotebookLM MCP. It does not contain NotebookLM, Google credentials, cookies, Chrome auth state, or MCP configuration.

## Upstream components

- [noVNC](https://github.com/novnc/noVNC)
- [websockify](https://github.com/novnc/websockify)
- [x11vnc](https://github.com/LibVNC/x11vnc)
- [Xvfb](https://www.x.org/releases/current/doc/man/man1/Xvfb.1.xhtml)
- [Chromium](https://www.chromium.org/)

The Dockerfile remains in this directory as the reproducible build source. The current Hermes Portainer Agent cannot build this image through its remote BuildKit path, so the image must be built and preloaded on the Hermes Docker host before the Git-backed stack is deployed.

Current image tag:

```text
homelab-novnc:20260910-1
```

Build or refresh it on the target host before changing the tag in the Compose file:

```bash
docker build -t homelab-novnc:YYYYMMDD novnc
```

Portainer uses `pull_policy: never` so it does not attempt to pull this host-local image or invoke the broken remote BuildKit path. The stack itself remains Git-backed and all container configuration remains controlled by the merged repository revision. This is a deliberate host-local image limitation and should be replaced with a registry-backed image pipeline when GHCR or another approved registry is available.

## Runtime design

- Virtual display: `:99`
- Resolution: `1280x800x24`
- Window manager: Fluxbox
- Internal raw VNC: port `5900`, loopback-only inside the container
- noVNC/websockify: port `6080`
- Browser profile: `${DATA_DIR}/data/chromium`
- Default host binding: loopback only
- Default browser page: `about:blank`

The raw VNC server uses `-nopw` because the host port is intended to remain loopback-only and access is through an SSH tunnel. Do not change `NOVNC_BIND_ADDRESS` to a LAN or public address without adding a real authentication boundary.

## Portainer variables

Copy the variable names from `example.env` into the Portainer stack environment. Keep the real values in Portainer and never commit a deployment-specific `.env` file.

- `DATA_DIR`: stable host data directory outside the Portainer Git checkout.
- `NOVNC_BIND_ADDRESS`: default `127.0.0.1`.
- `NOVNC_PORT`: host port, default `6080`.
- `DISPLAY_NUM`: virtual display number, default `99`.
- `SCREEN_RESOLUTION`: default `1280x800x24`.
- `ENABLE_VNC`: must be `true` for this stack.
- `START_BROWSER`: start Chromium automatically, default `true`.
- `BROWSER_URL`: initial browser URL, default `about:blank`.

Do not put passwords, Google credentials, cookies, tokens, private hostnames, endpoint IDs, or stack IDs in this repository.

## Portainer deployment

Create a Git-backed Portainer stack from this repository after the PR is merged:

- Compose path: `novnc/docker-compose.yml`
- Git updates: enabled according to the existing Portainer policy
- Persistent path: the Portainer `DATA_DIR` variable
- Published access: loopback by default

The image builds locally from the repository. Portainer must be able to build the Dockerfile from the Git checkout.

## SSH tunnel access

From the workstation, forward the remote loopback port:

```bash
ssh \
  -F /dev/null \
  -N \
  -T \
  -o ExitOnForwardFailure=yes \
  -L 127.0.0.1:16080:127.0.0.1:6080 \
  <user>@<novnc-host>
```

Open this locally:

```text
http://127.0.0.1:16080/vnc.html
```

Verify the tunnel before opening the page:

```bash
curl -I http://127.0.0.1:16080/vnc.html
```

## Validation

Render the Compose file with safe placeholder values:

```bash
docker compose --env-file novnc/example.env -f novnc/docker-compose.yml config
```

After deployment, verify all layers:

1. Portainer stack remains Git-backed and points to the merged `main` revision.
2. The container is running and healthy.
3. The persistent mount points to the configured stable data path.
4. `http://127.0.0.1:6080/vnc.html` responds on the target host.
5. The SSH tunnel works from the workstation.
6. A real browser desktop appears and Chromium is usable.
7. The desktop survives a controlled container restart.
8. Logs contain no permission errors or restart loop.

An HTTP 200 response alone is not sufficient proof that the VNC desktop works.

## Backup and rollback

The Chromium profile is potentially sensitive state. Include the configured data path in Backrest only after deciding that retaining browser state is appropriate. A pure rebuild is possible when browser state is disposable.

Rollback is to remove the Portainer stack while preserving the configured data path. Do not remove shared networks, reverse-proxy records, Authentik entries, or DNS records implicitly.
