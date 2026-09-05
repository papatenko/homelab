#!/bin/sh
set -eu
HEARTBEAT_PRODUCER=hermes-backrest
export HEARTBEAT_PRODUCER
exec "$(dirname "$0")/../run-heartbeat.sh"
