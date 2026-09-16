# Hister

Hister is a private, self-hosted search engine for indexed web pages and files.
This stack runs the official container on the NAS and is intended to remain LAN-only.

## Upstream

- Repository: <https://github.com/asciimoo/hister>
- Docker documentation: <https://hister.org/docs/docker>
- Configuration reference: <https://hister.org/docs/configuration>

## Portainer deployment

Create a Git-backed stack named `hister` on the NAS endpoint using this directory's
`docker-compose.yml`.

Set these stack variables in Portainer:

- `HISTER_IMAGE`: `ghcr.io/asciimoo/hister:latest`
- `HISTER_BIND_ADDRESS`: the NAS LAN address, not `0.0.0.0`
- `HISTER_PORT`: `4433`, unless the port is already in use
- `HISTER_BASE_URL`: `http://<NAS-LAN-IP>:4433`
- `HISTER_DATA_DIR`: a dedicated directory under the mounted NAS MISC filesystem

The data directory must be created on the NAS and writable by container UID/GID
`65532`. Do not place it in Portainer's Git checkout, and do not use an NFS/SMB
mount for Hister's SQLite state.

The published port is bound to the NAS LAN address so Hister is not exposed on
other host interfaces. Do not add router forwarding for this service.

## Initial setup

1. Open the LAN URL in a browser.
2. Install the Firefox or Chrome Hister extension.
3. Configure the extension to use the LAN Hister URL.
4. Visit a test page and confirm it appears in search.
5. If local files are needed, configure narrowly scoped directories and exclusions.

Hister stores indexed content and page previews in its data directory. Treat the
index as private data even though this deployment is LAN-only.

## Verification

- Container is running and healthy.
- The container mount points to the dedicated directory on the NAS MISC mount.
- The LAN URL returns the Hister web interface.
- A test page can be indexed and searched.
- Homepage links to the same LAN address.
- Uptime Kuma monitors the LAN URL without credentials.

## Rollback

Redeploy the previous Git revision through Portainer while preserving the Hister
data directory. Do not delete the data directory during a stack rollback.
