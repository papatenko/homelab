# Portainer stack storage layout

Persistent application data should live outside Portainer's Git checkout directory.

Portainer Git stacks are checked out under paths like:

```text
/data/compose/<stack-id>/
```

Those paths are Portainer-managed deployment workspaces. Do not rely on them for application state if the data needs to survive stack recreation, repo path changes, or cleanup.

## Convention

For stacks that need a local persistent data root, use `DATA_DIR`:

```env
DATA_DIR=/opt/stacks/pihole
```

`DATA_DIR` is intended to be **stack-scoped** in Portainer. Each stack can use the same variable name with a different value.

Examples:

```env
# Pi-hole stack
DATA_DIR=/opt/stacks/pihole

# Nginx Proxy Manager stack
DATA_DIR=/opt/stacks/nginxproxymanager

# Upsnap stack
DATA_DIR=/opt/stacks/upsnap

# Termix stack
DATA_DIR=/opt/stacks/termix

# Whisper stack
DATA_DIR=/opt/stacks/whisper

# Open Design stack
DATA_DIR=/opt/stacks/opendesign
```

Compose files should prefer this pattern:

```yaml
volumes:
  - ${DATA_DIR:-/opt/stacks/app-name}/config:/container/config
```

The fallback keeps a stack deployable even if `DATA_DIR` is not set, while Portainer can still override it per stack.

## Existing app-specific data variables

Some stacks already use app-specific data variables. Keep those when they are already clear:

```env
ACTUAL_DATA_DIR=/opt/stacks/actual
BACKREST_DATA_DIR=/opt/stacks/backrest
STIRLING_DATA_DIR=/opt/stacks/stirling
VAULTWARDEN_DATA_DIR=/opt/stacks/vaultwarden
WALLOS_DATA_DIR=/opt/stacks/wallos
```

Immich also already uses specific variables:

```env
UPLOAD_LOCATION=/opt/stacks/immich/library
DB_DATA_LOCATION=/opt/stacks/immich/postgres
```

Do not store the Immich Postgres database on a network share.

## Migration from repo-local config

If an existing stack used relative paths such as `./data` or `./etc-pihole`, copy that data from the old repo working tree on the Docker host into the new stack data root before redeploying.

Example:

```bash
sudo mkdir -p /opt/stacks/pihole
sudo rsync -a ~/homelab/pihole/etc-pihole/ /opt/stacks/pihole/etc-pihole/

sudo mkdir -p /opt/stacks/nginxproxymanager
sudo rsync -a ~/homelab/nginxproxymanager/data/ /opt/stacks/nginxproxymanager/data/
sudo rsync -a ~/homelab/nginxproxymanager/letsencrypt/ /opt/stacks/nginxproxymanager/letsencrypt/

sudo mkdir -p /opt/stacks/upsnap
sudo rsync -a ~/homelab/upsnap/data/ /opt/stacks/upsnap/data/

sudo mkdir -p /opt/stacks/canvas-todoist
sudo rsync -a ~/homelab/canvas-todoist/data/ /opt/stacks/canvas-todoist/data/

sudo mkdir -p /opt/stacks/openwebui/searxng
sudo rsync -a ~/homelab/openwebui/searxng/core-config/ /opt/stacks/openwebui/searxng/core-config/
```

Use trailing slashes on the source directory when you want to copy the contents into the destination directory.

## Media stack

The media stack intentionally keeps its existing path variables and is not part of this storage-layout refactor.
