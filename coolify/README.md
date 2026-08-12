# Coolify

This is the canonical Portainer-compatible definition for the Coolify control plane.

## Scope

The stack manages the Coolify control plane:

- Coolify application
- PostgreSQL
- Redis
- Realtime service
- Coolify-managed Traefik proxy
- Coolify sentinel

Coolify remains responsible for the application, database, and service containers that it deploys. Those child workloads are not intended to become separate Portainer stacks.

## Upstream sources

- [Coolify installation documentation](https://coolify.io/docs/get-started/installation)
- [Coolify Compose source](https://github.com/coollabsio/coolify/tree/v4.x)
- [Coolify releases](https://github.com/coollabsio/coolify/releases)

## Current migration image set

The definition uses current pinned releases where the upgrade is clear and keeps the stateful database/cache major versions unchanged for the first cutover:

- Coolify: `v4.3.0`
- Realtime: `1.0.17`
- Sentinel: `0.0.22`
- Traefik: `v3.7.10`
- PostgreSQL: `15-alpine`
- Redis: `7-alpine`

PostgreSQL and Redis remain on their existing major versions for the first cutover. PostgreSQL major-version changes require a deliberate dump/restore or in-place migration plan, and Redis major-version changes require compatibility validation. They should not be mixed into the ownership migration.

## Required Portainer variables

Set these in Portainer using the existing values. Never commit or paste the values into Git or chat:

- `COOLIFY_DATA_DIR`
- `DB_USERNAME`
- `DB_PASSWORD`
- `REDIS_PASSWORD`
- `PUSHER_APP_ID`
- `PUSHER_APP_KEY`
- `PUSHER_APP_SECRET`
- `COOLIFY_SENTINEL_TOKEN`

The existing host file at `${COOLIFY_DATA_DIR}/source/.env` remains mounted read-only into the Coolify container and remains the authoritative Coolify application environment. Its values must not be regenerated during migration.

The image, port, and process-tuning variables are documented in `example.env`. Override them only when the target host requires a different value.

## Persistent state

The definition preserves these host paths:

- `${COOLIFY_DATA_DIR}/applications`
- `${COOLIFY_DATA_DIR}/backups`
- `${COOLIFY_DATA_DIR}/databases`
- `${COOLIFY_DATA_DIR}/services`
- `${COOLIFY_DATA_DIR}/ssh`
- `${COOLIFY_DATA_DIR}/proxy`
- `${COOLIFY_DATA_DIR}/sentinel`
- `${COOLIFY_DATA_DIR}/source/.env`

It also reuses the existing named volumes:

- `coolify-db`
- `coolify-redis`

Backrest should continue covering `${COOLIFY_DATA_DIR}` and the two named-volume data paths. Backup configuration and restore testing are separate operational steps.

## Portainer deployment notes

Before deployment:

1. Merge this change into the repository's default branch.
2. Create a Git-backed Portainer stack from `coolify/docker-compose.yml`.
3. Configure the required variables using the existing values.
4. Confirm the `coolify` external Docker network exists.
5. Confirm the stack will reuse the existing named volumes and host paths.
6. Verify Portainer reports a populated Git configuration after creation and after any environment update.

The controlled migration must stop the original Coolify Compose projects before starting this stack, otherwise container names, ports, and the proxy will collide. The original source files and data must remain available for rollback.

## Validation

From the repository root:

```bash
docker compose --env-file coolify/example.env -f coolify/docker-compose.yml config
git diff --check
```

The example file contains placeholders only. It is for rendering and review, not deployment.

## Rollback

If migration is later attempted and fails:

1. Stop the Portainer Coolify stack without deleting volumes.
2. Leave `coolify-db`, `coolify-redis`, and `${COOLIFY_DATA_DIR}` intact.
3. Restart the original Coolify Compose projects from their preserved source files.
4. Verify the Coolify UI, database connection, existing applications, and proxy routes.
5. Keep the failed Portainer stack definition for diagnosis until rollback is confirmed.
