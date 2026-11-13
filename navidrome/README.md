# Navidrome

Self-hosted music server with a Subsonic API (works with Amperfy, Symfonium, Feishin, etc.),
plus two discovery companions:

- **Explo**: weekly ListenBrainz playlists ("Weekly Exploration", "Weekly Jams") built only from
  tracks already in the library. Downloads are off: every schedule passes `--download-mode=skip`.
- **Aurral**: artist discovery UI. Lidarr, downloaders and Flows are intentionally left unconfigured.

Upstream: [Navidrome docs](https://www.navidrome.org/docs/installation/docker/) ·
[Explo](https://github.com/LumePart/Explo) · [Aurral](https://github.com/lklynet/aurral)

## Paths

| Host path | Container | Notes |
|---|---|---|
| `${MUSIC_DIR}` (default `/mnt/misc/music`) | navidrome `/music:ro` | Music library. Navidrome never writes here. Smart playlists (`*.nsp`) also live here. |
| `${DATA_DIR}/data` | navidrome `/data` | SQLite DB, cache. Back up. |
| `${DATA_DIR}/explo/config` | explo `/opt/explo/config` | Explo `.env` written by its web UI, playlist cache. |
| `${DATA_DIR}/aurral/{config,data}` | aurral | Aurral state. |

## Ports and variables

See `example.env`. Ports: Navidrome 4533, Explo 7288, Aurral 3001. Only Navidrome is meant to be
published through the reverse proxy (use websockets; do not put forward-auth in front of it,
since Subsonic clients can't do the login redirect). Explo and Aurral stay LAN/Tailnet-only.

Secrets (`ND_LASTFM_*`, `LISTENBRAINZ_USER_TOKEN`, `EXPLO_*_PASSWORD`) are Portainer stack
variables only. Never commit them.

## First run

1. Open Navidrome on the LAN and create the admin user **before** publishing it.
2. In Navidrome, under Personal settings, link Last.fm and ListenBrainz scrobbling.
3. Create a non-admin Navidrome user for Explo and set `EXPLO_SYSTEM_USERNAME/PASSWORD`.
   Explo creates playlists for that user and marks them public so they show up for the main user.
   (Alternatively, use the main user.)

## Playlist import (`tools/playlist-sync`)

`sync_playlist.py` rebuilds an ordered Navidrome playlist from a CSV (`position,artist,title,…`).
It's re-runnable: each run replaces the playlist with every track that currently matches, and
writes `matched.csv`, `ambiguous.csv`, `missing.csv` and `missing.md` (with purchase search links).

```bash
ND_URL=http://<host>:4533 ND_USER=<user> ND_PASS=<pass> \
  python3 tools/playlist-sync/sync_playlist.py tools/playlist-sync/jim-time.csv "jim time (gym)" ./reports
```

Add `--dry-run` to report without touching the playlist. Remixes, slowed and sped-up edits are
treated as different recordings.

Options checked before writing it: tunesynctool (YT Music to Navidrome; skips unmatched tracks,
no missing report), SpotSonic and NaviSpot (Spotify-only, Exportify CSV / Spotify API). None
produces an ordered missing-track report or replaces the playlist in place on re-runs.

## Validation and rollback

- `curl http://<host>:4533/ping` returns OK, and the container is `healthy`.
- `docker logs explo` lists both schedules with `--download-mode=skip`.
- Rollback: stop the stack in Portainer. State is under `${DATA_DIR}` and the music folder is
  read-only, so removing the stack doesn't touch music files.
