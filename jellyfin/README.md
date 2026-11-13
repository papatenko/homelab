# Jellyfin

Media server for movies and TV, split out of `media-stack/` so players and downloaders deploy
independently. It mounts the shared media root (`MEDIA_ROOT`, default `/mnt/misc/media`) as `/data`.
Libraries live in `/data/library/{movies,tv,music}`. Appdata is `${DATA_DIR}/appdata/jellyfin`
(unchanged from the old media-stack, so an existing config carries over).

Upstream: https://jellyfin.org/docs/general/installation/container/

Not deployed as of 2026-11-13. Rollback/backup: the appdata directory; Jellyfin DB migrations prevent
downgrades, so keep the image version alongside backups.
