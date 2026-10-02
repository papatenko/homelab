#!/usr/bin/env bash
# Register a custom daemon's unit as a systemd user service so it shows up in
# Cockpit's Services -> User view. Usage: register-user-service.sh <unit-file>...
set -euo pipefail
[ $# -ge 1 ] || { echo "usage: $0 <path/to/name.service>..." >&2; exit 2; }

dest="$HOME/.config/systemd/user"
mkdir -p "$dest"
for unit in "$@"; do
  src="$(readlink -f "$unit")"
  [ -f "$src" ] || { echo "not found: $unit" >&2; exit 1; }
  name="$(basename "$src")"
  ln -sf "$src" "$dest/$name"
  systemctl --user daemon-reload
  systemctl --user enable --now "$name"
  systemctl --user is-active "$name"
done
