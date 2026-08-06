# Portainer GitOps Stack Management

All Portainer stacks should be **git-backed** via the GitHub repository.
Secrets live in Portainer's saved stack environment, never in Git.

## Architecture

```
GitHub repo  -->  Portainer (pull + deploy)  -->  Docker hosts
```

Each stack lives in its own directory:
```
<repo-root>/
  <stack-name>/
    docker-compose.yml    # compose definition (uses ${VAR} for secrets)
    example.env           # documented env vars (no real secrets)
    README.md             # stack-specific notes
```

## Converting Custom Stacks to Git-Backed

### Portainer CE Limitation

Portainer CE does **not** support in-place conversion of a custom stack to
git-backed. The relevant API behaviors:

- `PUT /api/stacks/{id}` **always detaches** git config
- `POST /api/stacks/{id}/git` requires the stack to **already have** git config
- `POST /api/stacks/create/{type}/repository` rejects duplicate stack names

The only supported path: **delete the custom stack, then recreate as git-backed**.

### Conversion Procedure

1. **Backup the stack env** (save all env vars from Portainer stack settings):
   ```bash
   curl -sk -H "X-API-Key: $PORTAINER_API_TOKEN" \
     https://<portainer-host>/api/stacks/<id> | jq '.Env'
   ```

2. **Verify the repo compose matches** the deployed stack file:
   ```bash
   curl -sk -H "X-API-Key: $PORTAINER_API_TOKEN" \
     https://<portainer-host>/api/stacks/<id>/file | jq -r '.StackFileContent' > /tmp/deployed.yml
   git show origin/main:<stack-dir>/docker-compose.yml > /tmp/repo.yml
   diff /tmp/repo.yml /tmp/deployed.yml
   ```

3. **Delete the custom stack** via Portainer UI (Stacks > select > Delete).
   Docker volumes are **not** removed -- data is preserved.

4. **Recreate as git-backed** via Portainer UI:
   - Stacks > Add stack > Repository
   - Name: (same as before)
   - Repository URL: (your homelab repo)
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
    - ${{MCP_PORT:-8009}}:8000
  ```
- **Profile gates**: stacks with optional services use `profiles:` + `COMPOSE_PROFILES`
  to prevent accidental deployment of unconfigured services

## Webhook Auto-Update (Optional)

For stacks that should auto-update on git push:

1. In Portainer stack settings, enable Auto-update via Webhook.
2. In GitHub repo Settings > Webhooks, add the Portainer webhook URL.
3. Only trigger on pushes to `main`.

**Do not enable auto-update on stacks with sensitive or complex configs**
until the deployment has been tested multiple times. The `COMPOSE_PROFILES`
gate provides additional safety (profile-gated services won't deploy unless
explicitly enabled in env).
