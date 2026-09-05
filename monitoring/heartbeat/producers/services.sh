#!/bin/sh
set -eu
HEARTBEAT_PRODUCER=services
export HEARTBEAT_PRODUCER
exec "$(dirname "$0")/../run-heartbeat.sh"
