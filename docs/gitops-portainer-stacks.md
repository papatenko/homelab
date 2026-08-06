# Portainer GitOps Stack Management

All Portainer stacks should be **git-backed** via the `papatenko/homelab` GitHub
repository. Secrets live in Portainer's saved stack environment, never in Git.

## Architecture

```
GitHub (papatenko/homelab)  ──>  Portainer (pull + deploy)  ──>  NAS / Raspi / Services
```

Each stack lives in its own directory:
```
papatenko/homelab/
  <stack-name>/
    docker-compose.yml    # compose definition (uses ${VAR} for secrets)
    example.env           # documented env vars (no real secrets)
    README.md             # stack-specific notes
```

## Stack Status

Last verified: 2026-08-06

| ID | Stack Name | Git-Backed | Endpoint | Host |
|----|------------|-----------|----------|------|
| 4 | actual | yes | 4 | NAS |
| 5 | vaultwarden | yes | 4 | NAS |
| 10 | **nextcloud** | **NO (custom)** | 4 | NAS |
| 11 | backrest | yes | 4 | NAS |
| 12 | watchtower | yes | 3 | Raspi |
| 16 | wallos | yes | 4 | NAS |
| 17 | watchtower | yes | 4 | NAS |
| 25 | immich | yes | 4 | NAS |
| 26 | upsnap | yes | 3 | Raspi |
| 28 | wgeasy | yes | 3 | Raspi |
| 29 | pihole | yes | 3 | Raspi |
| 30 | nginxproxymanager | yes | 3 | Raspi |
| 32 | **authentik** | **NO (custom)** | 3 | Raspi |
| 38 | homepage | yes | 3 | Raspi |
| 43 | whisper | yes | 6 | Services |
| 52 | motioneye | yes | 3 | Raspi |
| 53 | whisper | yes | 7 | Services |
| 55 | n8n | yes | 7 | Services |
| 56 | backrest | yes | 3 | Raspi |
| 63 | omada-controller | yes | 3 | Raspi |
| 64 | openviking | yes | 4 | NAS |
| 65 | omniroute | yes | 7 | Services |

**Portainer Endpoints:**
- 3 = Raspi (192.168.0.133)
- 4 = NAS (192.168.0.200)
- 6 = Services (192.168.0.201) — whisper
- 7 = Services (192.168.0.201) — whisper, n8n, omniroute

## Converting Custom Stacks to Git-Backed

### Portainer CE v2.39.2 Limitation

Portainer CE does **not** support in-place conversion of a custom stack to
git-backed. The relevant API behaviors:

- `PUT /api/stacks/{id}` **always detaches** git config (see `updateComposeStack`
  in `stack_update.go` line ~250: `stack.GitConfig = nil`)
- `POST /api/stacks/{id}/git` requires the stack to **already have** git config
  (returns 500 "No Git config in the found stack" otherwise)
- `POST /api/stacks/create/{type}/repository` rejects duplicate stack names

The only supported path: **delete the custom stack, then recreate as git-backed**.

### Conversion Procedure

1. **Backup the stack env** (save all env vars from Portainer stack settings):
   ```bash
   curl -sk -H "X-API-Key: $PORTAINER_API_TOKEN"      https://192.168.0.133:9443/api/stacks/<id> | jq '.Env'
   ```

2. **Verify the repo compose matches** the deployed stack file:
   ```bash
   curl -sk -H "X-API-Key: $PORTAINER_API_TOKEN"      https://192.168.0.133:9443/api/stacks/<id>/file | jq -r '.StackFileContent' > /tmp/deployed.yml
   git show origin/main:<stack-dir>/docker-compose.yml > /tmp/repo.yml
   diff /tmp/repo.yml /tmp/deployed.yml
   ```

3. **Delete the custom stack** via Portainer UI (Stacks > select > Delete).
   Docker volumes are **not** removed — data is preserved.

4. **Recreate as git-backed** via Portainer UI:
   - Stacks > Add stack > Repository
   - Name: (same as before)
   - Repository URL: `https://github.com/papatenko/homelab.git`
   - Compose path: `<stack-dir>/docker-compose.yml`
   - Reference: `refs/heads/main`
   - Re-enter all env vars from the backup

5. **Verify**: stack shows "Repository" source in the UI; containers healthy.

### Risk Notes

- Container images are already cached on the target host (no pull delay).
- Named volumes persist across stack deletion (database, data dirs intact).
- Downtime is typically 1-5 minutes (docker-compose down + up).
- Always confirm container health after recreation.

## New Stack Workflow

When adding a new stack to the homelab:

1. Create `<stack-name>/` directory in the repo with:
   - `docker-compose.yml` (use `${VAR}` for secrets, never hardcode)
   - `example.env` (document every env var with descriptions and defaults)
   - `README.md` (setup notes, service URLs, dependencies)

2. Commit and push (or open a PR).

3. In Portainer UI: Stacks > Add stack > Repository > point to the new directory.

4. Set all required env vars in the Portainer stack settings.

5. Enable `COMPOSE_PROFILES` if the stack uses profile-gated services.

## Environment Variable Conventions

- **Secrets** (passwords, tokens, keys): stored in Portainer stack env only
- **Config** (hostnames, ports, paths): use `${VAR}` references in compose,
  with default values in the compose file where safe:
  ```yaml
  ports:
    - ${MCP_PORT:-8009}:8000
  ```
- **Profile gates**: stacks with optional services use `profiles:` + `COMPOSE_PROFILES`
  to prevent accidental deployment of unconfigured services

## Webhook Auto-Update (Optional)

For stacks that should auto-update on git push:

1. In Portainer stack settings, enable Auto-update via Webhook.
2. In GitHub repo Settings > Webhooks, add the Portainer webhook URL:
   `https://192.168.0.133:9443/api/webhooks/<webhook-id>`
3. Only trigger on pushes to `main`.

**Do not enable auto-update on stacks with sensitive or complex configs**
until the deployment has been tested multiple times. The `COMPOSE_PROFILES`
gate provides additional safety (profile-gated services won't deploy unless
explicitly enabled in env).
