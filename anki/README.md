# Anki sync server

Runs the official Anki headless sync implementation. Study takes place in Anki clients, not in a web UI. [Upstream documentation](https://docs.ankiweb.net/sync-server.html).

## Status

Draft only. Do not deploy or expose publicly until the security, secret-delivery, update, backup, and client-sync gates below are complete.

## Configuration

- `SYNC_USER1`: Anki `username:password` or a supported hash. Provide through the approved secret manager integration, never commit a value. Exact delivery into the running container is not yet validated.
- `ANKI_BIND_ADDRESS` and `ANKI_PORT`: private host binding, reachable by the reverse proxy but restricted from unintended access.
- `ANKI_DATA_DIR`: absolute persistent host directory, writable by UID/GID 10001. It must be distinct from client collections.

The container's service listens on HTTP port 8080. Terminate HTTPS at the reverse proxy and protect the proxy-to-server network. A private bind address alone does not prove firewall isolation. Do not put browser-only forward authentication in front of native Anki clients without testing.

## Image updates

The Dockerfile installs the current Anki Python package **when built**, not when a running container restarts. Portainer Git polling does not automatically rebuild it when upstream releases change. A documented, tested image rebuild and deployment workflow is required before production. Confirm client/server compatibility and retain a rollback image and backup when upgrading.

## Deployment and verification gates

1. Verify the target Portainer endpoint, architecture, mount path, free host port, and secure credential delivery. Qualify the Git-stack remote build before relying on it.
2. Configure HTTPS reverse proxy and restrict direct upstream access. Test client routes, negative authentication, certificate, and media upload limits.
3. Verify persistent data ownership, backup coverage, completed snapshot, and isolated restore. Use a consistent database backup method.
4. Test sync of a disposable card and media across two clients and after a restart. Do not overwrite an existing collection during a full-sync prompt.
5. Add a service-appropriate TCP monitor with the established notification route. A successful TCP probe does not prove synchronization works.

Retain the persistent data and client exports during rollback. Do not use `down -v` or delete the data directory. The Homepage link opens the Anki website, not a hosted study interface.
