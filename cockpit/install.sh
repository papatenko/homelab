#!/usr/bin/env bash
# Install Cockpit on the Fedora workstation, bound to Tailscale + localhost only.
# Idempotent. Uses pkexec (agent shells have no TTY for sudo).
set -euo pipefail

PORT=9090
TS_IP="$(tailscale ip -4 2>/dev/null | head -n1 || true)"
[ -n "$TS_IP" ] || { echo "tailscale has no IPv4; refusing to bind Cockpit more widely" >&2; exit 1; }

DROPIN=$(mktemp)
cat >"$DROPIN" <<CONF
[Socket]
ListenStream=
ListenStream=127.0.0.1:${PORT}
ListenStream=${TS_IP}:${PORT}
FreeBind=yes
CONF

pkexec bash -c "
  set -e
  rpm -q cockpit-system cockpit-ws >/dev/null 2>&1 || dnf install -y cockpit-system cockpit-ws
  install -d /etc/systemd/system/cockpit.socket.d
  install -m 644 '$DROPIN' /etc/systemd/system/cockpit.socket.d/listen.conf
  systemctl daemon-reload
  systemctl enable cockpit.socket
  systemctl restart cockpit.socket
"
rm -f "$DROPIN"

systemctl is-active cockpit.socket
ss -ltn "sport = :${PORT}" | tail -n +2
echo "Cockpit: https://<tailscale-ip>:${PORT} (Services -> User)"
