# Docker image cleanup

These host-level systemd units schedule Docker's native image prune daily at 03:30 host local time with up to ten minutes randomized delay. The `until=168h` filter refers to image creation time, not time since becoming unused. All images unreferenced by any running or stopped container, including tagged images, may be removed. Containers, volumes, networks, and build cache are not pruned. Rollback may require pulling an old image by digest.

After review and merge, install both units into `/etc/systemd/system/` on the intended Docker host, run `systemctl daemon-reload`, then `systemctl enable --now docker-image-prune.timer`. Confirm with `systemctl list-timers docker-image-prune.timer` and inspect the journal after its first scheduled run. To disable, run `systemctl disable --now docker-image-prune.timer`. Do not run the service manually as a syntax test, it deletes eligible images.

These units contain no secrets. Back up host-specific units, scripts, credentials and enablement state separately in an encrypted backup; repository storage alone is not a backup of host credentials or runtime state.
