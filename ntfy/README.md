# ntfy

This is a Git-backed Compose definition for a private, local ntfy notification broker.
It is intentionally not wired to a public hostname, reverse proxy, identity provider, or
Telegram credential.

## Upstream and image

- Documentation: <https://docs.ntfy.sh/>
- Docker deployment: <https://docs.ntfy.sh/install/#docker>
- Image: `binwiederhier/ntfy:v2.28.0` (official release; upstream publishes Linux ARM64 artifacts)

The image tag is pinned for reproducible review and ARM64 deployment. Update it only after
checking the upstream release and image manifest for the target host architecture.

## Secure defaults

- State is a local bind mount at `${NTFY_DATA_DIR:-/opt/stacks/ntfy}`. Do not place it on NAS/NFS.
- Published port binds to `${NTFY_BIND_ADDRESS:-127.0.0.1}` by default, so it is not public.
  If LAN/VPN clients need access, the coordinator may set this to the host's private interface
  address during runtime setup; never bind `0.0.0.0` without a separately reviewed firewall policy.
- `NTFY_AUTH_DEFAULT_ACCESS=deny` is explicit. Anonymous publish/subscribe is not enabled.
- No token, password, bot credential, or Docker socket is stored in Git or Compose.

## Coordinator-only runtime setup

The coordinator performs these steps on the target host/Portainer stack after the Git change is
reviewed. Workers must not provision credentials or deploy remotely.

1. Create the local data directory with ownership/permissions appropriate for the ntfy image.
2. Run the repository preflight on the target host before rendering or deploying:

   ```bash
   NTFY_BIND_ADDRESS=<approved-private-address> \
   NTFY_PORT=<approved-port> \
   NTFY_DATA_DIR=<local-directory> \
   NTFY_BASE_URL=<matching-private-url> \
   ./ntfy/preflight.sh
   ```

   The preflight rejects unspecified/public bindings, non-local storage, missing or
   unwritable data directories, and a base URL that does not resolve to the bind address.
3. Render the stack with the same non-secret variables and verify the bind address remains
   loopback or a private LAN/VPN interface. `NTFY_BASE_URL` is required and must match the
   direct bind address and port, so generated links cannot silently remain on loopback.
4. Start the stack and verify the `/v1/health` container healthcheck becomes healthy.
5. Provision separate ntfy identities using the supported `ntfy user` commands (or the approved
   control-plane equivalent): a write-only producer identity for heartbeat publishers and a
   read-only consumer identity for readers. Store credentials only in the approved secret store.
6. Grant each identity only the required topic ACLs. Do not put credentials in stack files,
   shell arguments, logs, chat, or this repository.
7. Run a synthetic authenticated publish/subscribe test without printing credentials.

There is no unauthenticated bootstrap mode in this definition. If a first-boot procedure ever
requires temporarily disabling auth to create the auth database, that must be an explicit,
coordinator-only maintenance gate: bind loopback only, block all other access, create users,
restore `NTFY_AUTH_DEFAULT_ACCESS=deny`, restart, and verify anonymous requests are rejected.
Workers must not add or enable such a gate.

## Validation

```bash
docker compose -f ntfy/compose.yaml --env-file ntfy/.env.example config
```

The example file contains no secrets and is suitable for config rendering only. Deployment is
not part of this worker change.

## Backup and rollback

Back up the local data directory through the existing host backup policy. To roll back, stop the
stack, restore the prior Git revision and preserved data directory, then verify auth and topics.
Do not delete the data directory as part of routine rollback.
