# Anki sync server

Runs the official Anki headless sync implementation. Study takes place in Anki clients, not in a web UI. [Upstream documentation](https://docs.ankiweb.net/sync-server.html).

## Status

Draft only. Do not deploy or expose publicly until the security, secret-delivery, update, backup, and client-sync gates below are complete.

## Configuration

- `SYNC_USER1`: Anki `username:password` or a supported hash. Supply through the Portainer environment editor. Never commit or log a value.
- `ANKI_BIND_ADDRESS` and `ANKI_PORT`: private host binding, reachable by the reverse proxy but restricted from unintended access.
- `ANKI_DATA_DIR`: absolute persistent host directory, writable by UID/GID 10001. It must be distinct from client collections.

The container's service listens on HTTP port 8080. Terminate HTTPS at the reverse proxy and protect the proxy-to-server network. A private bind address alone does not prove firewall isolation. Do not put browser-only forward authentication in front of native Anki clients without testing.

## Image updates

Portainer's remote build can fail during BuildKit negotiation. As a temporary fallback the stack uses a host-local image tagged to the reviewed Dockerfile commit, `anki-sync:9dde3b1`, with `pull_policy: never`. Build that exact Dockerfile on the target Docker host before stack creation. This is not a registry-backed or automatically updated image. Git polling and container restarts do not update the Anki package. For updates, review the Dockerfile and upstream release, build a new commit-tagged image, update this reference in a PR, and retain a rollback image and backup. A registry-backed update workflow remains future work.

## Deployment and verification gates

1. Verify the target Portainer endpoint, architecture, mount path, free host port, and secure credential delivery. Qualify the Git-stack remote build before relying on it.
2. Configure HTTPS reverse proxy and restrict direct upstream access. Test client routes, negative authentication, certificate, and media upload limits.
3. Verify persistent data ownership, backup coverage, completed snapshot, and isolated restore. Use a consistent database backup method.
4. Test sync of a disposable card and media across two clients and after a restart. Do not overwrite an existing collection during a full-sync prompt.
5. Add a service-appropriate TCP monitor with the established notification route. A successful TCP probe does not prove synchronization works.

Retain the persistent data and client exports during rollback. Do not use `down -v` or delete the data directory. Set Homepage's `HOMEPAGE_VAR_ANKI_URL` to the deployed HTTPS origin without a trailing slash. The Homepage entry opens and monitors `/health`; it is not a hosted study interface. Confirm HTTPS reachability from Homepage and verify the card after deployment. Health indicates server availability, not successful synchronization.
