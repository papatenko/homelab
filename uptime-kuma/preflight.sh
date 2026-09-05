#!/bin/sh
# Validate Kuma's private bind and local SQLite state path before deployment.
set -eu

bind_address=${KUMA_BIND_ADDRESS:-127.0.0.1}
port=${KUMA_PORT:-3001}
data_dir=${KUMA_DATA_DIR:-/opt/stacks/uptime-kuma}

fail() {
  printf 'uptime-kuma preflight: %s\n' "$1" >&2
  exit 1
}

case "$data_dir" in
  /*) ;;
  *) fail 'KUMA_DATA_DIR must be an absolute host path' ;;
esac
[ "$data_dir" != / ] || fail 'KUMA_DATA_DIR must not be the host root'
[ -d "$data_dir" ] || fail "KUMA_DATA_DIR does not exist: $data_dir (create it on the coordinator host)"
[ -w "$data_dir" ] || fail "KUMA_DATA_DIR is not writable: $data_dir"

command -v findmnt >/dev/null 2>&1 || fail 'findmnt is required to verify local storage'
fstype=$(findmnt -T "$data_dir" -no FSTYPE 2>/dev/null || true)
[ -n "$fstype" ] || fail "could not determine the filesystem for KUMA_DATA_DIR: $data_dir"
case "$fstype" in
  nfs|nfs4|cifs|smb|smb3|9p|sshfs|fuse.sshfs|ceph|ceph.*)
    fail "KUMA_DATA_DIR is on a network filesystem ($fstype); use local disk" ;;
esac

command -v python3 >/dev/null 2>&1 || fail 'python3 is required for address validation'
python3 - "$bind_address" "$port" <<'PY'
import ipaddress
import sys

bind, port_text = sys.argv[1:]
try:
    address = ipaddress.ip_address(bind)
except ValueError:
    raise SystemExit(f"KUMA_BIND_ADDRESS must be an IP address: {bind}")
if address.is_unspecified or address.is_multicast or address.is_reserved:
    raise SystemExit("KUMA_BIND_ADDRESS must not be an unspecified, multicast, or reserved address")
if not address.is_loopback and not (address.is_private or address in ipaddress.ip_network("100.64.0.0/10")):
    raise SystemExit("KUMA_BIND_ADDRESS must be loopback or a private LAN/VPN address")
try:
    port = int(port_text)
except ValueError:
    raise SystemExit("KUMA_PORT must be an integer")
if not 1 <= port <= 65535:
    raise SystemExit("KUMA_PORT must be between 1 and 65535")
PY

printf 'uptime-kuma preflight: OK (bind=%s, fs=%s)\n' "$bind_address" "$fstype"
