#!/bin/bash
set -Eeuo pipefail

: "${DISPLAY_NUM:=99}"
: "${SCREEN_RESOLUTION:=1280x800x24}"
: "${VNC_PORT:=5900}"
: "${NOVNC_PORT:=6080}"
: "${DATA_DIR:=/data}"
: "${ENABLE_VNC:=true}"
: "${START_BROWSER:=true}"
: "${BROWSER_URL:=about:blank}"

export DISPLAY=":${DISPLAY_NUM}"
mkdir -p "${DATA_DIR}" "${DATA_DIR}/chromium"

cleanup() {
  trap - EXIT INT TERM
  jobs -pr | xargs -r kill 2>/dev/null || true
}
trap cleanup EXIT INT TERM

if [[ "${ENABLE_VNC,,}" != "true" ]]; then
  echo "[novnc] ENABLE_VNC is not true" >&2
  exit 1
fi

Xvfb "${DISPLAY}" -screen 0 "${SCREEN_RESOLUTION}" -ac -nolisten tcp &
fluxbox >/tmp/fluxbox.log 2>&1 &
x11vnc -display "${DISPLAY}" -forever -shared -localhost -rfbport "${VNC_PORT}" -nopw -xkb >/tmp/x11vnc.log 2>&1 &
websockify --web=/usr/share/novnc "${NOVNC_PORT}" "localhost:${VNC_PORT}" >/tmp/websockify.log 2>&1 &
websockify_pid=$!

for _ in {1..30}; do
  if wget --quiet --spider "http://127.0.0.1:${NOVNC_PORT}/vnc.html"; then
    break
  fi
  sleep 1
done

if ! wget --quiet --spider "http://127.0.0.1:${NOVNC_PORT}/vnc.html"; then
  echo "[novnc] noVNC did not become ready" >&2
  exit 1
fi

echo "[novnc] Ready at /vnc.html on port ${NOVNC_PORT}"

if [[ "${START_BROWSER,,}" == "true" ]]; then
  chromium \
    --disable-dev-shm-usage \
    --no-first-run \
    --no-default-browser-check \
    --user-data-dir="${DATA_DIR}/chromium" \
    "${BROWSER_URL}" >/tmp/chromium.log 2>&1 &
fi

while kill -0 "${websockify_pid}" 2>/dev/null; do
  sleep 5
done

echo "[novnc] websockify exited" >&2
exit 1
