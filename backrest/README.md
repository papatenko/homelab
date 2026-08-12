# Backrest

This is the canonical Backrest Compose definition for every Docker host in the homelab.

Deploy the same `backrest/docker-compose.yml` through Portainer on each host, using host-specific stack variables. Do not create a second Compose definition for an individual machine.

## Host-specific variables

- `BACKREST_DATA_DIR`: stable Backrest state directory on the target host.
- `BACKUP_SOURCE_PATH`: host path exposed read-only as `/userdata`.
- `PORTAINER_DATA_PATH`: host path exposed read-only as `/portainer-data`. Set it to that host's Portainer data path when applicable. On hosts without Portainer, set it to an existing harmless readable path and do not include `/portainer-data` in the plan.
- `BACKREST_PORT`: host-published UI port.
- `BACKREST_CONTAINER_NAME` and `BACKREST_HOSTNAME`: only needed when the default names would collide.
- `TIMEZONE`: host-local timezone.

Backrest state is kept outside the Portainer Git checkout. Backup sources are mounted read-only because Backrest only needs to read them.

Each host should use its own repository identity or repository path and its own plan identity, while sharing the same Compose source. Exclude disposable data, such as Whisper data or camera recordings, in the relevant host's Backrest plan rather than changing this shared Compose file.
