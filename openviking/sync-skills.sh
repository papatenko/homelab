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
state_file="${OPENVIKING_SKILLS_STATE_FILE:-/var/lib/openviking/skills-sync-state.json}"

if [[ ! -d "$vault_skills" ]]; then
  printf 'ERROR: skills source directory not found: %s\n' "$vault_skills" >&2
  exit 1
fi

state_dir="$(dirname "$state_file")"
mkdir -p "$state_dir"
chmod 700 "$state_dir"
touch "$state_file"
chmod 600 "$state_file"

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

  digest="$(sha256sum "$skill_file" | awk '{print $1}')"
  if python3 - "$state_file" "$name" "$digest" <<'PY'
import json
import sys
from pathlib import Path

state_path, name, digest = sys.argv[1:]
try:
    state = json.loads(Path(state_path).read_text() or "{}")
except (OSError, json.JSONDecodeError):
    state = {}
raise SystemExit(0 if state.get(name) == digest else 1)
PY
  then
    printf 'SKIP: %s (unchanged)\n' "$name"
    continue
  fi

  python3 - "$skill_file" > "$payload_file" <<'PY'
import json
import sys
from pathlib import Path

path = sys.argv[1]
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
    python3 - "$state_file" "$name" "$digest" <<'PY'
import json
import os
import sys
import tempfile
from pathlib import Path

state_path, name, digest = sys.argv[1:]
path = Path(state_path)
try:
    state = json.loads(path.read_text() or "{}")
except (OSError, json.JSONDecodeError):
    state = {}
state[name] = digest
fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
try:
    with os.fdopen(fd, "w") as stream:
        json.dump(state, stream, sort_keys=True)
        stream.write("\n")
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)
finally:
    try:
        os.unlink(temporary)
    except FileNotFoundError:
        pass
PY
    ok=$((ok + 1))
  else
    printf 'FAIL (%s): %s\n' "$status" "$name" >&2
    fail=$((fail + 1))
  fi
done < <(find "$vault_skills" -type f -name SKILL.md -print0)

printf 'Synced %d skills, %d failed\n' "$ok" "$fail"
(( fail == 0 ))
