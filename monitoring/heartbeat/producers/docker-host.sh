#!/bin/sh
set -eu
HEARTBEAT_PRODUCER=docker-host
export HEARTBEAT_PRODUCER
exec "$(dirname "$0")/../run-heartbeat.sh"
