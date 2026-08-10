# OpenViking vault index

A dedicated, Git-managed Portainer stack for read-only, derived indexing of an authoritative Obsidian vault. Deployment-specific paths, addresses, and URLs are supplied through Portainer or a host-local environment file, not stored in this repository.

## Scope

Only these container paths are imported:

- `/vault/wiki` to `viking://resources/obsidian/wiki`
- `/vault/mocs` to `viking://resources/obsidian/mocs`
- `/vault/skills` to `viking://resources/obsidian/skills`

The source mounts are read-only. OpenViking never writes to the source vault.

## Portainer deployment

Create or update a Git-backed stack using `openviking/docker-compose.yml`. Set every required value in `example.env`, including:

- `OPENVIKING_BIND_ADDRESS`, the private address where the service should listen
- `OPENVIKING_PUBLIC_BASE_URL`, the externally reachable HTTPS base URL
- `OPENVIKING_DATA_DIR`, the deployment host's persistent state directory
- `OPENVIKING_WIKI_PATH`, `OPENVIKING_MOC_PATH`, and `OPENVIKING_SKILLS_PATH`, the source directories

Do not use `0.0.0.0` for the bind address. Do not commit these values to Git. Keep the source mounts read-only and expose the service only through the intended private or authenticated route.

The embeddings service has no published port. It supplies local `nomic-embed-text` embeddings and stores its state below `OPENVIKING_DATA_DIR`.

## First-time initialization

After the stack is running, prepare the embedding model and initialize OpenViking using the deployment's container names:

```bash
docker exec openviking-embeddings ollama pull nomic-embed-text
docker exec -it openviking openviking-server init
docker exec openviking openviking-server doctor
```

Choose the embeddings service as the Ollama endpoint and choose the configured VLM provider. Keep OAuth state and API keys in the restricted state directory or a secret manager. Create a least-privilege user key for scheduled synchronization and client access. Never commit or paste a root key into a client configuration.

## Resource refresh timer

The existing resource refresh timer imports the three approved container paths and uses stable resource URIs. Install its files using paths appropriate for the deployment host, then provide a root-owned mode-0600 environment file containing:

```text
OPENVIKING_URL=<local-or-private-service-url>
OPENVIKING_API_KEY=<least-privilege-user-key>
OPENVIKING_ACCOUNT=<account>
OPENVIKING_USER=<user>
```

The refresh script does not use a network address fallback. It requires `OPENVIKING_URL` and `OPENVIKING_API_KEY`.

## Skills synchronization timer

`sync-skills.sh` synchronizes local `SKILL.md` files below `VAULT_SKILLS_DIR`:

1. It hashes each file and skips unchanged skills, avoiding unnecessary VLM calls and token usage.
2. It submits changed or new skills with `POST /api/v1/skills`.
3. If a skill already exists, it updates it with `PUT /api/v1/skills/{name}`.
4. It records successful content hashes in a restricted state file.
5. It rejects invalid skill names before making a request.
6. It uses temporary files created by `mktemp` and removes them on exit.
7. It reports each failure and exits nonzero if any skill fails.

Install the script and service using deployment-local paths. The checked-in service intentionally references generic locations:

```bash
install -d -m 0700 /etc/openviking /usr/local/libexec
install -m 0700 sync-skills.sh /usr/local/libexec/openviking-sync-skills.sh
install -m 0644 systemd/openviking-sync-skills.service /etc/systemd/system/
install -m 0644 systemd/openviking-sync-skills.timer /etc/systemd/system/
```

Create `/etc/openviking/sync-skills.env` with values appropriate to the host:

```text
OPENVIKING_SECRETS_ENV=<path-to-root-owned-secrets-file>
OPENVIKING_SKILLS_STATE_FILE=<optional-state-file-path>
```

The referenced secrets file must contain:

```text
OPENVIKING_URL=<local-or-private-service-url>
OPENVIKING_API_KEY=<least-privilege-user-key>
VAULT_SKILLS_DIR=<host-local-skills-directory>
```

Enable and test the hourly timer:

```bash
systemctl daemon-reload
systemctl enable --now openviking-sync-skills.timer
systemctl start openviking-sync-skills.service
systemctl status openviking-sync-skills.timer
```

## Client access

Use `OPENVIKING_PUBLIC_BASE_URL` when configuring an authenticated MCP client. Use a dedicated user key and restrict the client to retrieval and health tools where the client supports tool allowlists. Do not authorize mutating or watch-management tools for a retrieval-only client.

## Validation

```bash
curl -fsS "${OPENVIKING_PUBLIC_BASE_URL}/health"
docker inspect openviking --format '{{range .Mounts}}{{println .Destination .RW}}{{end}}'
docker exec openviking sh -c 'test -r /vault/wiki && test -r /vault/mocs && test -r /vault/skills && ! touch /vault/wiki/.write-test'
docker exec openviking ov find 'known wiki fact' --path viking://resources/obsidian/wiki
docker exec openviking ov find 'known MOC topic' --path viking://resources/obsidian/mocs
docker exec openviking ov find 'known skill' --path viking://resources/obsidian/skills
```

For a change test, edit a harmless note through the normal vault workflow, wait for the relevant timer, query the corresponding resource, and verify that the source file remains unchanged by the container.
