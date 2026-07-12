# Omada Controller

TP-Link Omada Software Controller packaged by `mbentley/docker-omada-controller`.

## Upstream sources

- Project: https://github.com/mbentley/docker-omada-controller
- Upstream Compose: https://github.com/mbentley/docker-omada-controller/blob/master/docker-compose.yml
- Device adoption notes: https://github.com/mbentley/docker-omada-controller/blob/master/DEVICE_ADOPTION.md
- Image: `mbentley/omada-controller:6.2`

`mbentley/omada-controller:6.2` publishes `linux/amd64` and `linux/arm64` images.

## What it runs

- Service: `omada-controller`
- Network mode: `host`
- Web UI:
  - HTTP: `8088`
  - HTTPS: `8043`
- Portal HTTPS: `8843`
- Discovery/adoption/management ports:
  - UDP `27001`, `29810`
  - TCP `29811`-`29817`
- Data path: `${DATA_DIR:-/opt/stacks/omada-controller}/data`
- Logs path: `${DATA_DIR:-/opt/stacks/omada-controller}/logs`

Host networking is used intentionally. Omada device discovery and adoption are much cleaner when the controller is directly on the host network instead of hidden behind Docker bridge NAT.

## Portainer variables

Copy `example.env` into Portainer stack variables and adjust as needed.

Important defaults:

```env
OMADA_IMAGE=mbentley/omada-controller:6.2
OMADA_MANAGE_HTTPS_PORT=8043
OMADA_JAVA_MAX_HEAP_SIZE=512m
OMADA_MONGOD_EXTRA_ARGS=--wiredTigerCacheSizeGB 0.25
```

The memory-related defaults are conservative for small hosts. Increase them if the controller manages many devices or logs show memory pressure.

## Persistent data

Persistent state lives outside Portainer's Git checkout:

```text
/opt/stacks/omada-controller/data
/opt/stacks/omada-controller/logs
```

Use the controller's built-in backup feature before upgrades or destructive changes.

## Nginx Proxy Manager

Optional. If exposing the management UI through NPM, point the proxy host at the Docker host on HTTPS port `8043`. Expect Omada's own certificate behavior unless custom certs are configured.

Device adoption still depends on Omada discovery/inform ports, not just the web UI proxy. Do not proxy adoption ports through NPM.

## Authentik

Omada has its own login system. Use Authentik/NPM forward-auth only as an additional gate for the web UI after confirming it does not break controller sessions or device workflows.

## API key / agent access

No API token is created by this stack. If automation later needs controller API access, create a dedicated Omada admin/API credential with minimum necessary permissions and store it outside Git, for example in `pass` under `infra/omada-controller/api-token`.

## Validation

After deployment:

1. Verify the container is running and healthy.
2. Open `https://<host>:8043/` from the LAN.
3. Complete the Omada first-run setup or restore a backup.
4. Confirm data and logs are written under `/opt/stacks/omada-controller`.
5. If devices do not adopt, read upstream `DEVICE_ADOPTION.md` and verify discovery/inform ports before changing the container.

## Rollback

If deployment fails:

1. Stop/remove the Portainer stack.
2. Remove any dedicated NPM proxy host, if created.
3. Remove any dedicated Authentik app/provider, if created.
4. Preserve `/opt/stacks/omada-controller` until Justin confirms the data can be deleted.
