#!/bin/sh
set -eu
HEARTBEAT_PRODUCER=nas-rsync
export HEARTBEAT_PRODUCER
exec "$(dirname "$0")/../run-heartbeat.sh"
