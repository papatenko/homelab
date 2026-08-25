#!/bin/sh
# Runs as the unprivileged tokentracker user. `tracker serve` only binds
# 127.0.0.1 (no --host flag or env override exists upstream —
# src/commands/serve.js, LOCAL_BIND_HOST), so it can't be published from a
# container as-is. socat forwards the container's public interface to that
# loopback socket. See Dockerfile for the full explanation.
#
# We deliberately never pass --port / $PORT to `tracker serve`: doing so
# flips on its own ensurePortFree() pre-flight (src/commands/serve.js), which
# shells out to `lsof -ti tcp:$port` and SIGKILLs whatever pids it returns.
# Under some container/kernel combinations (observed under WSL2) that command
# returns bogus pids including 1, killing the container's own init. Instead
# we let tracker pick its own default port and discover it from its startup
# log line, so this works regardless of which port it lands on (7680 normally,
# 7681 if it detects a WSL-style kernel and works around the Windows
# Delivery Optimization service — see serve.js WSL_DEFAULT_PORT).
set -eu

PUBLIC_PORT="${TOKENTRACKER_PORT:-7680}"
LOG_FILE="$(mktemp)"

tracker serve --no-open ${TOKENTRACKER_SYNC_FLAG:-} >"$LOG_FILE" 2>&1 &
TRACKER_PID=$!

cleanup() {
  kill "$TRACKER_PID" 2>/dev/null || true
  wait "$TRACKER_PID" 2>/dev/null || true
  rm -f "$LOG_FILE"
}
trap cleanup TERM INT

# Tail tracker's own stdout so it's still visible in `docker logs`, and watch
# for the port it actually bound to.
tail -f "$LOG_FILE" &
TAIL_PID=$!

INTERNAL_PORT=""
for _ in $(seq 1 30); do
  INTERNAL_PORT="$(grep -oE 'http://127\.0\.0\.1:[0-9]+' "$LOG_FILE" \
    | grep -oE '[0-9]+$' | tail -n1 || true)"
  [ -n "$INTERNAL_PORT" ] && break
  sleep 1
done
: "${INTERNAL_PORT:=$PUBLIC_PORT}"

socat TCP-LISTEN:"$PUBLIC_PORT",fork,reuseaddr TCP:127.0.0.1:"$INTERNAL_PORT" &
SOCAT_PID=$!

wait "$TRACKER_PID" "$SOCAT_PID" "$TAIL_PID"
