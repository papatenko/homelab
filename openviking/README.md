# OpenViking vault index

A dedicated, Git-managed Portainer stack for read-only, derived indexing of the authoritative Nextcloud Obsidian vault. The MCP endpoint is exposed through the `openviking.papatenko.org` reverse-proxy route with OpenViking's native API-key and OAuth protection.

## Scope

Only these read-only container paths are importable:

- `/vault/wiki` → `viking://resources/obsidian/wiki`
- `/vault/skills` → `viking://resources/obsidian/skills`

The host mounts are fixed to the server-side Nextcloud directories in `docker-compose.yml`. They are not mounted anywhere writable. The refresh script also excludes `.raw/`, `inbox/`, `journal/`, and `templates/` if any appear below either approved source root.

## Persistent state and backup policy

`OPENVIKING_DATA_DIR` defaults to `/mnt/misc/appdata/openviking`. It contains configuration, Codex OAuth state, local embedding models, and derived OpenViking indexes only. During this pilot, exclude the entire directory from scheduled backups. The source vault remains authoritative and is never modified by OpenViking.

Create restricted paths before deployment:

```bash
install -d -m 0700 /mnt/misc/appdata/openviking/{secrets,bin}
install -m 0700 refresh-resources.sh /mnt/misc/appdata/openviking/bin/refresh-resources.sh
install -m 0644 systemd/openviking-refresh.service /etc/systemd/system/
install -m 0644 systemd/openviking-refresh.timer /etc/systemd/system/
```

## Portainer deployment

Use a Git-backed Portainer stack from this repository, with Compose path `openviking/docker-compose.yml`, Git updates enabled, and the values from `example.env`.

Set `OPENVIKING_BIND_ADDRESS` to the NAS LAN address in Portainer. Do not set it to `0.0.0.0`. The public hostname is `openviking.papatenko.org`, and Nginx Proxy Manager forwards it to the NAS address on port 1933.

The image's native health check serves `GET /health` on port 1933. The `embeddings` container has no published port and supplies local `nomic-embed-text` embeddings. This keeps VLM processing on Codex OAuth without requiring a separate embedding API credential.

## First-time initialization

After the stack is running, prepare the local embedding model:

```bash
docker exec openviking-embeddings ollama pull nomic-embed-text
```

Run the official interactive setup on the NAS:

```bash
docker exec -it openviking openviking-server init
docker exec openviking openviking-server doctor
```

Choose an Ollama embedding provider with model `nomic-embed-text`, endpoint `http://embeddings:11434`, and dimension `768`. Choose **OpenAI Codex** for the VLM and complete its OAuth login. The OAuth credential remains only under the restricted `OPENVIKING_DATA_DIR`; never add it to this repository or to the vault.

Configure the server to require authentication before LAN exposure. Generate the root key on the NAS, store the server config and refresh credential only under the restricted state directory, then create a least-privilege user key for developer clients. Do not use development mode on a LAN address.

The refresh service requires this root-owned mode-0600 file, which is not versioned:

```bash
# /mnt/misc/appdata/openviking/secrets/refresh.env
OPENVIKING_URL=http://127.0.0.1:1933
OPENVIKING_API_KEY=<restricted OpenViking user key>
OPENVIKING_ACCOUNT=justin
OPENVIKING_USER=refresh
```

Then enable the 15-minute NAS-side timer:

```bash
systemctl daemon-reload
systemctl enable --now openviking-refresh.timer
systemctl start openviking-refresh.service
systemctl status openviking-refresh.timer
```

The timer only executes `ov add-resource` against the two read-only mount paths and stable resource URIs. It does not use OpenViking's internal watcher and therefore cannot mutate the vault.

## Claude Code and Codex lifecycle integration

Install the official plugin separately on each developer machine that runs the client, not inside the NAS container. Configure that machine's `~/.openviking/ovcli.conf` with the NAS LAN URL and a dedicated USER key. The official installer is idempotent:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/volcengine/OpenViking/main/examples/memory-plugin-shared/install.sh)
```

For manual installation, use `claude plugin marketplace add https://raw.githubusercontent.com/volcengine/OpenViking/main/.claude-plugin/marketplace.json` then `claude plugin install openviking-memory@openviking`; for Codex use `codex plugin marketplace add volcengine/OpenViking` then `codex plugin add openviking-memory@openviking`.

Set these environment variables in the Claude Code and Codex launch environment:

```bash
OPENVIKING_AUTO_RECALL=true
OPENVIKING_AUTO_CAPTURE=false
OPENVIKING_MEMORY_ENABLED=true
```

For Codex, also ensure `~/.codex/config.toml` includes:

```toml
[features]
plugin_hooks = true
```

Install from the official OpenViking marketplace, then approve the hooks in a fresh client session. `OPENVIKING_AUTO_CAPTURE=false` is mandatory for this pilot, so recall remains automatic while session content is never written to OpenViking.

## Antigravity

Use OpenViking's native `/mcp` endpoint as a private, manually invoked retrieval MCP server, configured with a dedicated USER key and the NAS LAN URL. Do not install the lifecycle plugin or set automatic-recall/capture variables for Antigravity in this phase.

The native endpoint exposes additional mutating tools to any USER key. In Antigravity, explicitly allow only the retrieval/health tools (`find`, `search`, `read`, `ls`, `health`) and do not authorize `remember`, `add_resource`, `forget`, or watch-management tools. If Antigravity cannot enforce a tool allowlist, defer this connection rather than presenting the native endpoint as read-only.

## Claude Web and ChatGPT Web

Use the public MCP endpoint:

```text
https://openviking.papatenko.org/mcp
```

Both clients should use OAuth when adding the connector. OpenViking publishes the OAuth metadata required for dynamic client registration and then prompts for an OpenViking API key in its consent page. Do not paste the root server key into either client. Use a dedicated USER key and restrict the client to retrieval tools where the client supports tool allowlists.

Before adding the connector, verify that the metadata advertises the new hostname rather than the former `viking.papatenko.org` hostname:

```bash
curl -fsS https://openviking.papatenko.org/.well-known/oauth-authorization-server
curl -fsS https://openviking.papatenko.org/.well-known/oauth-protected-resource
```

## Validation

```bash
# NAS health and non-public bind
curl -fsS http://127.0.0.1:1933/health
ss -ltnp | grep ':1933'
docker inspect openviking --format '{{range .Mounts}}{{println .Source .Destination .RW}}{{end}}'

# Verify derived state survives restart
docker compose restart openviking
docker ps --filter name=^/openviking$ --format '{{.Status}}'

# Verify read-only mounts, then stable resource namespaces
docker exec openviking sh -c 'test -r /vault/wiki && test -r /vault/skills && ! touch /vault/wiki/.openviking-write-test'
docker exec openviking ov find 'known wiki fact' --path viking://resources/obsidian/wiki
docker exec openviking ov find 'known skill' --path viking://resources/obsidian/skills
```

For the change test, edit one harmless note through the existing vault workflow, wait at least one timer interval, query the matching resource, and compare its source-file checksum before and after. Do not edit vault files from the OpenViking container.
