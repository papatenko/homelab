#!/usr/bin/env bash
set -euo pipefail

# Synchronize local SKILL.md files into OpenViking's skills namespace.
# OPENVIKING_SECRETS_ENV, OPENVIKING_URL, and VAULT_SKILLS_DIR are required.

secrets_env="${OPENVIKING_SECRETS_ENV:?Set OPENVIKING_SECRETS_ENV in the service environment}"

if [[ ! -f "$secrets_env" ]]; then
  printf 'ERROR: secrets environment file not found: %s\n' "$secrets_env" >&2
  exit 1
fi

# shellcheck disable=SC1090
source "$secrets_env"

server_url="${OPENVIKING_URL:?Set OPENVIKING_URL in the secrets environment}"
vault_skills="${VAULT_SKILLS_DIR:?Set VAULT_SKILLS_DIR in the secrets environment}"
api_key="${OPENVIKING_API_KEY:?Set OPENVIKING_API_KEY in the secrets environment}"

if [[ ! -d "$vault_skills" ]]; then
  printf 'ERROR: skills source directory not found: %s\n' "$vault_skills" >&2
  exit 1
fi

payload_file="$(mktemp)"
response_file="$(mktemp)"
curl_config_file="$(mktemp)"
chmod 600 "$curl_config_file"
printf 'header = "X-API-Key: %s"\nheader = "Content-Type: application/json"\n' \
  "$api_key" > "$curl_config_file"
cleanup() {
  rm -f "$payload_file" "$response_file" "$curl_config_file"
}
trap cleanup EXIT

ok=0
fail=0
while IFS= read -r -d '' skill_file; do
  name="$(basename "$(dirname "$skill_file")")"
  if [[ ! "$name" =~ ^[A-Za-z0-9_-]{1,64}$ ]]; then
    printf 'FAIL: invalid skill directory name: %s\n' "$name" >&2
    fail=$((fail + 1))
    continue
  fi

  python3 - "$skill_file" "$name" > "$payload_file" <<'PY'
import json
import sys
from pathlib import Path

path, name = sys.argv[1:]
print(json.dumps({"data": Path(path).read_text()}))
PY

  if status=$(curl --silent --show-error \
      --output "$response_file" --write-out '%{http_code}' \
      --request POST "$server_url/api/v1/skills" \
      --config "$curl_config_file" \
      --data-binary "@$payload_file"); then
    :
  else
    status="curl-error:$?"
  fi

  if [[ "$status" == "409" ]]; then
    if status=$(curl --silent --show-error \
        --output "$response_file" --write-out '%{http_code}' \
        --request PUT "$server_url/api/v1/skills/$name" \
        --config "$curl_config_file" \
        --data-binary "@$payload_file"); then
      :
    else
      status="curl-error:$?"
    fi
  fi

  if [[ "$status" == "200" || "$status" == "201" ]]; then
    printf 'OK: %s\n' "$name"
    ok=$((ok + 1))
  else
    printf 'FAIL (%s): %s\n' "$status" "$name" >&2
    fail=$((fail + 1))
  fi
done < <(find "$vault_skills" -type f -name SKILL.md -print0)

printf 'Synced %d skills, %d failed\n' "$ok" "$fail"
(( fail == 0 ))
