# Semaphore UI

Web UI and scheduler for Ansible playbooks (replaces PatchMon for fleet patching). Source: https://github.com/semaphoreui/semaphore

Pinned to v2.20.23; PostgreSQL pinned to major 17. Both are excluded from Watchtower so upgrades are deliberate.

Portainer must supply `POSTGRES_PASSWORD`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `ACCESS_KEY_ENCRYPTION` (base64, 32 bytes) and `SEMAPHORE_BIND_ADDRESS` (private LAN address). Generate secrets through the approved secret manager, never Git. The port is not forwarded by the router, so access is LAN only.

Back up the `postgres_data` and `semaphore_data` volumes; losing `ACCESS_KEY_ENCRYPTION` makes stored keys unrecoverable. Roll back by removing only this stack and keeping volumes and secrets.
