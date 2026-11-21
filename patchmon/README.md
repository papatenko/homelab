# PatchMon

PatchMon provides a central package inventory and patch management interface. Agents run with elevated privileges. Use verified HTTPS and restrict access at the reverse proxy.

Source: https://github.com/PatchMon/PatchMon/tree/v2.1.8/docker

The application is deliberately pinned to 2.1.8 pending a controlled upgrade policy. PostgreSQL is pinned to major version 17. Automatic image updates are disabled for this stack to prevent unreviewed application/database compatibility changes.

Portainer must supply `PROXY_NETWORK`, `TRUSTED_PROXY_RANGES`, `CORS_ORIGIN`, `JWT_SECRET`, `SESSION_SECRET`, `AI_ENCRYPTION_KEY`, `POSTGRES_PASSWORD`, and `REDIS_PASSWORD`. Generate unique secrets through the approved secret manager. `CORS_ORIGIN` must match the HTTPS interface URL. The server has no host-published port and joins the existing proxy network. Restrict proxy access to trusted network ranges and verify the restriction independently.

Named volumes hold PostgreSQL and Redis state. Establish backup coverage and test database restoration before relying on scheduled updates. Stop/remove only this stack for rollback and retain volumes and secrets. Do not enable patch policies until existing update ownership, host identities, backups, scope, and a supervised canary have been verified. No RDP gateway is included.
