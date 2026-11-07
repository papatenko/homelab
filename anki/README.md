# Anki sync server

This stack runs the Anki project's headless sync server. Clients provide the flashcard interface. See https://docs.ankiweb.net/sync-server.html.

This definition is a work in progress and is not approved for production. Before deployment, qualify Portainer remote builds, a secure injected `SYNC_USER1`, persistent-directory ownership (UID/GID 10001), a private upstream route to an HTTPS reverse proxy, backup and restore, client synchronization, and an image rebuild/update policy. Portainer Git polling alone does not update the Python package inside an existing image.

Required runtime variables: `SYNC_USER1` (credential, never commit), `ANKI_BIND_ADDRESS`, `ANKI_PORT`, and `ANKI_DATA_DIR`. The data directory must be separate from client collections. Do not expose the unencrypted upstream publicly.
