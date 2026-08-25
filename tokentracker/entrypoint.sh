#!/bin/sh
# Runs as root: bind-mounted volumes arrive owned by the host UID, so reclaim
# them for the unprivileged tokentracker user before dropping root and
# handing off to run-tracker.sh.
set -eu

chown -R tokentracker:tokentracker /home/tokentracker

exec su-exec tokentracker /usr/local/bin/run-tracker.sh
