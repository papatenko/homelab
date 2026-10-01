# ActivityWatch server

Self-hosted [ActivityWatch](https://activitywatch.net/) server that collects window and AFK activity from desktop clients. Runs on the Services host and is reachable **only over Tailscale**.

> **WARNING: the ActivityWatch API has no authentication and no HTTPS.** Anyone who can reach port 5600 can read and write all activity data. Bind only to the Services Tailscale IP. Never put it behind Nginx Proxy Manager, public DNS, router port forwarding, or Tailscale Funnel.

## Image

There is no official ActivityWatch Docker image. This stack uses the community image [`ghcr.io/graphichealer/aw-server-docker`](https://github.com/GraphicHealer/aw-server-docker), which downloads the official ActivityWatch release zip (`v0.13.2`) on `debian:bookworm-slim`.

Notes from review:

- The container runs `aw-server/aw-server` from the release (the Python server, despite the upstream README saying aw-server-rust) using the Werkzeug development server. Acceptable for a single-user tailnet-only service.
- The image runs as root by default and the data volume is `/config` (via `XDG_CONFIG_HOME`/`XDG_DATA_HOME`). This stack runs it as `AW_UID:AW_GID` with `read_only`, `cap_drop: ALL`, and `no-new-privileges`.
- The image ships no `wget` or `curl`; the healthcheck uses bash `/dev/tcp`.
- The upstream CMD uses `--cors-origins *`; this stack overrides it to the tailnet URL.
- Upstream's scheduled rebuild workflow last ran 2026-04-22. The ref is digest-pinned and labelled `com.centurylinklabs.watchtower.enable=false`, so update it by hand: resolve a new digest with `docker buildx imagetools inspect ghcr.io/graphichealer/aw-server-docker:latest`, review, and change `AW_IMAGE` in Portainer.

## Deploy (Portainer, Services endpoint)

1. On the Services host, create the data directory owned by the container user:

   ```bash
   sudo install -d -o 1000 -g 1000 -m 750 /opt/stacks/activitywatch/data
   ```

   (Use your `AW_UID`/`AW_GID` if different. The container cannot create `/config/activitywatch` otherwise, and `cap_drop: ALL` removes root's permission override.)
2. In Portainer, select the **Services** endpoint, then Stacks, Add stack, Repository: this repo, compose path `activitywatch/docker-compose.yml`.
3. Set the variables from `example.env`. `AW_BIND_ADDRESS` must be the Services Tailscale IP (`tailscale ip -4` on that host).
4. Deploy, then check `http://<Services-Tailscale-IP>:5600/api/0/info` from a tailnet device.

## Client setup (desktop)

Run only the watchers locally; do not run a local `aw-server`, so data is not split.

- KDE Wayland: install [`awatcher`](https://github.com/2e3s/awatcher) (window + idle watcher).
- Edit `~/.config/activitywatch/aw-client/aw-client.toml`:

  ```toml
  [server]
  hostname = "100.89.183.56"
  port = "5600"
  ```

- Remove `aw-server` from `autostart_modules` in `aw-qt.toml` if using aw-qt.

## Links

- [ActivityWatch docs: remote server](https://docs.activitywatch.net/en/latest/remote-server.html)
- [ActivityWatch releases](https://github.com/ActivityWatch/activitywatch/releases)
- [GraphicHealer/aw-server-docker](https://github.com/GraphicHealer/aw-server-docker)
