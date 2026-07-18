#!/usr/bin/env bash
# Create and validate a local PostgreSQL backup for the n8n stack.
set -euo pipefail

DATA_DIR="${DATA_DIR:-/opt/stacks/n8n}"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-n8n-postgres}"
POSTGRES_DB="${POSTGRES_DB:-n8n}"
POSTGRES_USER="${POSTGRES_USER:-n8n}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
BACKUP_DIR="${DATA_DIR}/backups/postgres"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
FINAL_PATH="${BACKUP_DIR}/n8n-${STAMP}.dump"
TEMP_PATH="${FINAL_PATH}.partial"

mkdir -p "$BACKUP_DIR"
trap 'rm -f "$TEMP_PATH"' EXIT

docker exec "$POSTGRES_CONTAINER" \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom \
  > "$TEMP_PATH"

docker exec -i "$POSTGRES_CONTAINER" pg_restore --list < "$TEMP_PATH" >/dev/null
mv "$TEMP_PATH" "$FINAL_PATH"
find "$BACKUP_DIR" -type f -name 'n8n-*.dump' -mtime "+${RETENTION_DAYS}" -delete
trap - EXIT

printf 'Validated PostgreSQL backup: %s\n' "$FINAL_PATH"
