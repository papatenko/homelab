# arr-stack (acquisition)

Downloader, indexers and *arr managers. Players are separate stacks: `navidrome/` (music) and
`jellyfin/` (video). Each container is defined once, and nothing runs unless its profile is enabled.

| Profile | Services |
|---|---|
| `vpn` | gluetun (WireGuard) + qBittorrent, which shares gluetun's network and fails closed if the tunnel drops |
| `music` | prowlarr, lidarr (:8686) |
| `video` | prowlarr, sonarr, radarr, bazarr, jellyseerr |

Set `COMPOSE_PROFILES` in Portainer, e.g. `music` first, then `vpn,music` once the WireGuard
variables are populated.

## Data layout (hardlinks)

Every app mounts `MEDIA_ROOT` (default `/mnt/misc/media`) as `/data`:

```
/data/downloads/{incomplete,music,movies,tv}   qBittorrent save paths / categories
/data/library/{music,movies,tv}                 *arr root folders; players read these
/data/appdata/<app>                             (via DATA_DIR) app config
```

Because downloads and library share one mount and filesystem, imports are hardlinks, so there's
no double disk use while seeding. Configure qBittorrent's default save path as `/data/downloads`, the
incomplete path as `/data/downloads/incomplete`, and give Lidarr the category `music`
(→ `/data/downloads/music`) with root folder `/data/library/music`.

## Secrets

The WireGuard values (`WIREGUARD_*`) and any API keys are Portainer stack variables only.

Upstream: [Servarr Docker guide](https://wiki.servarr.com/docker-guide) ·
[TRaSH hardlinks](https://trash-guides.info/File-and-Folder-Structure/) ·
[Lidarr image](https://docs.linuxserver.io/images/docker-lidarr/) ·
[Gluetun](https://github.com/qdm12/gluetun-wiki)
