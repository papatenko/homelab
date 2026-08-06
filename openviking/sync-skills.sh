#!/usr/bin/env bash
set -euo pipefail

# Sync Obsidian vault SKILL.md files into OpenViking's skills namespace.
# Mirrors refresh-resources.sh: reads the API key from the secrets env file
# and POSTs each SKILL.md to /api/v1/skills (create-or-update).

secrets_env="${OPENVIKING_SECRETS_ENV:-/mnt/misc/appdata/openviking/secrets/refresh.env}"
server_url="${OPENVIKING_URL:-http://192.168.0.200:1933}"
vault_skills="${VAULT_SKILLS_DIR:-/mnt/nextcloud/Justin Kondratenko/files/Apps/Obsidian/skills}"

if [[ ! -f "$secrets_env" ]]; then
  echo "ERROR: secrets env not found: $secrets_env" >&2
  exit 1
fi

# shellcheck disable=SC1090
source "$secrets_env"

if [[ -z "${OPENVIKING_API_KEY:-}" ]]; then
  echo "ERROR: OPENVIKING_API_KEY not set in $secrets_env" >&2
  exit 1
fi

if [[ ! -d "$vault_skills" ]]; then
  echo "ERROR: skills vault not found: $vault_skills" >&2
  exit 1
fi

ok=0
fail=0
tmp_payload="$(mktemp)"

cleanup() {
  rm -f "$tmp_payload"
}
trap cleanup EXIT

while IFS= read -r -d '' skill_file; do
  name=$(basename "$(dirname "$skill_file")")

  # Build JSON payload: {"data": "<raw skill content>"}
  python3 -c '
import json, sys
with open(sys.argv[1]) as f:
    print(json.dumps({"data": f.read()}))
' "$skill_file" > "$tmp_payload"

  http_code=$(curl -sS -o /tmp/sync-skills-response.json -w "%{http_code}" \
    -X POST "$server_url/api/v1/skills" \
    -H "X-API-Key: $OPENVIKING_API_KEY" \
    -H "Content-Type: application/json" \
    --data-binary @"$tmp_payload" || true)

  if [[ "$http_code" == "200" ]]; then
    echo "OK: $name"
    ok=$((ok + 1))
  else
    err=$(head -c 300 /tmp/sync-skills-response.json 2>/dev/null || echo "no response body")
    echo "FAIL ($http_code): $name -> $err"
    fail=$((fail + 1))
  fi
  rm -f /tmp/sync-skills-response.json
done < <(find "$vault_skills" -name SKILL.md -print0)

echo "Synced $ok skills, $fail failed"
[[ $fail -eq 0 ]]
