# motionEye

Web frontend for the `motion` camera daemon, intended for camera monitoring and motion detection.

## Upstream sources

- Project: https://github.com/motioneye-project/motioneye
- Official Docker Compose: https://github.com/motioneye-project/motioneye/blob/main/docker/docker-compose.yml
- Docker docs: https://github.com/motioneye-project/motioneye/blob/main/docker/README.md
- Image: `ghcr.io/motioneye-project/motioneye:edge`
- Verified image platforms include `linux/arm64` and `linux/arm/v7`.

## What it runs

- Service: `motioneye`
- Web UI/internal port: `8765`
- Default stream port: `8081`
- Config path: `${DATA_DIR:-/opt/stacks/motioneye}/config`
- Video/media path: `${DATA_DIR:-/opt/stacks/motioneye}/videos`

The upstream compose currently uses the `edge` image. Keep that tag until the upstream project publishes a stable GHCR release tag suitable for this deployment.

## Persistent data

Persistent state is outside Portainer's Git checkout:

```text
/opt/stacks/motioneye/config
/opt/stacks/motioneye/videos
```

## Nginx Proxy Manager

Optional. If exposed through NPM, point the proxy host to the Docker host on port `8765`.

Recommended exposure model:

- LAN-only first.
- If public access is needed, put it behind HTTPS and an auth gate.
- Do not expose stream port `8081` publicly unless a specific camera/stream use case requires it.

## Authentication

motionEye has built-in user/admin authentication that should be configured after first boot.

If public access is required, prefer one of these patterns after confirming scope:

1. Built-in motionEye authentication plus HTTPS through NPM.
2. Authentik/NPM forward-auth in front of the app if a stronger SSO gate is desired.

## API key / agent access

No API key is created by this stack. If an automation or Hermes integration later needs access, create a least-privilege credential in motionEye and store it outside Git, for example in `pass` under `infra/motioneye/<credential-name>`.

## Validation

After deployment:

1. Verify the container is running and healthy.
2. Open the web UI on port `8765` from the LAN.
3. Complete initial motionEye admin setup.
4. Confirm config and videos are written under `/opt/stacks/motioneye`.
5. Check container logs for camera, permissions, or CPU-related errors.

## Rollback

If deployment fails:

1. Remove the Portainer stack.
2. Remove any dedicated NPM proxy host, if created.
3. Remove any dedicated Authentik app/provider, if created.
4. Preserve `/opt/stacks/motioneye` until Justin confirms the data can be deleted.
