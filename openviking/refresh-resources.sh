#!/usr/bin/env bash
set -euo pipefail

container="${OPENVIKING_CONTAINER:-openviking}"
server_url="${OPENVIKING_URL:?OPENVIKING_URL is required}"
api_key="${OPENVIKING_API_KEY:?OPENVIKING_API_KEY is required}"
export OPENVIKING_API_KEY
account="${OPENVIKING_ACCOUNT:-justin}"
user="${OPENVIKING_USER:-justin}"

# The two local paths exist only inside the container and are mounted read-only
# by docker-compose.yml. Reusing the same `--to` URI updates the resource in
# place, so this timer never creates timestamped resource namespaces.
refresh() {
  local source="$1"
  local target="$2"
  docker exec \
    -e OPENVIKING_CREDENTIAL_SOURCE=env \
    -e OPENVIKING_URL="$server_url" \
    -e OPENVIKING_API_KEY \
    -e OPENVIKING_ACCOUNT="$account" \
    -e OPENVIKING_USER="$user" \
    "$container" \
    ov add-resource "$source" --to "$target" --wait --watch-interval 0 \
      --exclude '.raw/**' --exclude 'inbox/**' --exclude 'journal/**' --exclude 'templates/**'
}

refresh /vault/wiki viking://resources/obsidian/wiki
refresh /vault/mocs viking://resources/obsidian/mocs
refresh /vault/skills viking://resources/obsidian/skills
