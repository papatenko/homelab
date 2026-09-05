#!/bin/sh
set -eu
HEARTBEAT_PRODUCER=raspberry-pi
export HEARTBEAT_PRODUCER
exec "$(dirname "$0")/../run-heartbeat.sh"
