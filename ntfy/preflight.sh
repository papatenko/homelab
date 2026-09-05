#!/bin/sh
# Validate ntfy's private bind, URL pairing, and local state path before deployment.
set -eu

bind_address=${NTFY_BIND_ADDRESS:-127.0.0.1}
base_url=${NTFY_BASE_URL:-}
port=${NTFY_PORT:-8080}
data_dir=${NTFY_DATA_DIR:-/opt/stacks/ntfy}

fail() {
  printf 'ntfy preflight: %s\n' "$1" >&2
  exit 1
}

[ -n "$base_url" ] || fail 'NTFY_BASE_URL is required; set it alongside NTFY_BIND_ADDRESS'
case "$data_dir" in
  /*) ;;
  *) fail 'NTFY_DATA_DIR must be an absolute host path' ;;
esac
[ "$data_dir" != / ] || fail 'NTFY_DATA_DIR must not be the host root'
[ -d "$data_dir" ] || fail "NTFY_DATA_DIR does not exist: $data_dir (create it on the coordinator host)"
[ -w "$data_dir" ] || fail "NTFY_DATA_DIR is not writable: $data_dir"

command -v findmnt >/dev/null 2>&1 || fail 'findmnt is required to verify local storage'
fstype=$(findmnt -T "$data_dir" -no FSTYPE 2>/dev/null || true)
[ -n "$fstype" ] || fail "could not determine the filesystem for NTFY_DATA_DIR: $data_dir"
case "$fstype" in
  nfs|nfs4|cifs|smb|smb3|9p|sshfs|fuse.sshfs|ceph|ceph.*)
    fail "NTFY_DATA_DIR is on a network filesystem ($fstype); use local disk" ;;
esac

command -v python3 >/dev/null 2>&1 || fail 'python3 is required for address and URL validation'
python3 - "$bind_address" "$port" "$base_url" <<'PY'
import ipaddress
import sys
from urllib.parse import urlsplit

bind, port_text, base_url = sys.argv[1:]
try:
    address = ipaddress.ip_address(bind)
except ValueError:
    raise SystemExit(f"NTFY_BIND_ADDRESS must be an IP address: {bind}")
if address.is_unspecified or address.is_multicast or address.is_reserved:
    raise SystemExit("NTFY_BIND_ADDRESS must not be an unspecified, multicast, or reserved address")
if not address.is_loopback and not (address.is_private or address in ipaddress.ip_network("100.64.0.0/10")):
    raise SystemExit("NTFY_BIND_ADDRESS must be loopback or a private LAN/VPN address")
try:
    port = int(port_text)
except ValueError:
    raise SystemExit("NTFY_PORT must be an integer")
if not 1 <= port <= 65535:
    raise SystemExit("NTFY_PORT must be between 1 and 65535")

parts = urlsplit(base_url)
if parts.scheme not in {"http", "https"} or not parts.hostname:
    raise SystemExit("NTFY_BASE_URL must be an absolute http(s) URL")
if parts.username or parts.password or parts.query or parts.fragment:
    raise SystemExit("NTFY_BASE_URL must not contain credentials, a query, or a fragment")
try:
    parts.port
except ValueError:
    raise SystemExit("NTFY_BASE_URL contains an invalid port")

host = parts.hostname.strip("[]").lower()
try:
    url_address = ipaddress.ip_address(host)
    url_is_loopback = url_address.is_loopback
except ValueError:
    url_is_loopback = host == "localhost"
try:
    url_port = parts.port or (443 if parts.scheme == "https" else 80)
except ValueError:
    raise SystemExit("NTFY_BASE_URL contains an invalid port")
if url_port != port:
    raise SystemExit("NTFY_BASE_URL port must match NTFY_PORT for this direct, non-proxied stack")
if address.is_loopback and not url_is_loopback:
    raise SystemExit("loopback binding requires a loopback NTFY_BASE_URL")
if not address.is_loopback and url_is_loopback:
    raise SystemExit("private LAN/VPN binding requires a non-loopback NTFY_BASE_URL")

try:
    resolved = {item[4][0] for item in __import__("socket").getaddrinfo(host, url_port, type=__import__("socket").SOCK_STREAM)}
except OSError as exc:
    raise SystemExit(f"NTFY_BASE_URL hostname does not resolve on the coordinator host: {host}") from exc
if str(address) not in resolved:
    raise SystemExit("NTFY_BASE_URL must resolve to NTFY_BIND_ADDRESS; verify both values are paired")
PY

printf 'ntfy preflight: OK (bind=%s, base URL=%s, fs=%s)\n' "$bind_address" "$base_url" "$fstype"
