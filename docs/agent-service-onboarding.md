# Agent Workflow: Add a Homelab Service

This workflow is written for humans and coding agents. Use it only when adding a new service to this homelab repository and deploying it through Portainer.

The key idea: **discover upstream, codify in Git, deploy from Portainer, then optionally expose/auth/integrate.**

This runbook follows the repo's current layout: **service directories live at the repository root**. Do not create a `services/` directory as part of normal service onboarding. The separate repo organization plan is long-term planning material, not an instruction to reorganize while adding a service.

## Safety Rules

- Open PRs freely for repo changes.
- Do **not** make SSH, sudo, Portainer, Nginx Proxy Manager, Authentik, DNS, or API-token changes without Justin confirming the exact target and scope.
- Do not commit secrets. Use `example.env`, Portainer stack variables, `pass`, or Bitwarden.
- Prefer Git-backed Portainer stacks with Git updates enabled.
- Persistent data must live outside Portainer's Git checkout. See [`storage-layout.md`](storage-layout.md).
- Keep public Git generic: avoid LAN IPs, private domains, hostnames, and tokens unless explicitly approved.
- Keep the PR scoped to adding the requested service. Do not reorganize existing directories or introduce new top-level categories unless Justin explicitly asks for a repo reorganization.

## Step 1 — Find the Upstream Docker Compose

Start with official sources:

1. Official docs.
2. Official GitHub/GitLab repository.
3. Official `compose.yaml` / `docker-compose.yml`.
4. Official Docker run command that can be translated into Compose.
5. Maintained community examples only if upstream has no good Compose source.

Record:

- Upstream docs URL.
- Image names and versions.
- Required ports.
- Required volumes.
- Required environment variables.
- Secrets and generation commands.
- Healthcheck/readiness endpoint.
- Authentication model.
- Reverse-proxy requirements: base URL, websockets, upload limits, trusted proxy headers.
- Resource needs: CPU, RAM, disk, GPU, architecture.

Do not blindly copy demo Compose. Fix persistence, secrets, restart policy, and image tags for this repo.

## Step 2 — Recommend the Target Machine

Before deployment, recommend where the service should run.

Consider:

- Architecture compatibility: amd64 vs arm64.
- Port conflicts.
- Storage needs and backup expectations.
- Public vs LAN-only exposure.
- Data sensitivity.
- CPU/GPU requirements.
- Proximity to Nginx Proxy Manager, Authentik, NAS storage, or existing dependencies.

Use this format in PRs or comments:

```text
Recommended host: <host or role>
Reason:
- <reason 1>
- <reason 2>
Tradeoffs:
- <main tradeoff>
Needs confirmation before deployment: yes
```

## Step 3 — Add the Service to the Repo Root

Current repo convention is one service directory at repo root, for example:

```text
whisper/
  docker-compose.yml
  example.env
  README.md
```

When adding a new service, follow this root-directory convention. Do not place the new service under `services/` for normal onboarding.

Required files:

```text
<service>/
  docker-compose.yml      # or compose.yaml if adjacent services use it
  example.env             # placeholders only; no secrets
  README.md               # deployment and integration notes
```

Do not move existing stacks while adding a service. If the service needs shared documentation or automation, add only the minimum files required for that service and document follow-up work in the PR.

### Compose Guidelines

- Use stable persistent host paths through variables.
- Prefer `DATA_DIR=/opt/stacks/<service>` unless a service-specific variable is clearer.
- Use defaults that keep the stack deployable if a variable is missing:

```yaml
volumes:
  - ${DATA_DIR:-/opt/stacks/example}/data:/app/data
```

- Add `restart: unless-stopped` unless upstream says not to.
- Pin image tags when practical.
- Add a healthcheck when a reliable endpoint/command exists.
- Avoid committing `.env`; commit `example.env` only.
- Avoid repo-relative persistent data paths such as `./data`.

### README Checklist

Each service README should include:

- Purpose.
- Upstream source links.
- Recommended host and rationale.
- Portainer stack name and compose path.
- Required Portainer variables.
- Persistent data paths.
- Nginx Proxy Manager notes, if exposed.
- Authentik/OIDC/forward-auth notes, if used.
- API-key notes, if Hermes or integrations use the service.
- Validation and rollback notes.

## Step 4 — Open a PR

Use a branch like:

```text
feat/add-<service>-stack
```

PR body should include:

```markdown
## Summary
- Add <service> stack
- Add example env and deployment notes

## Upstream sources
- <docs URL>
- <compose URL>

## Host recommendation
Recommended host: <host or role>
Reason:
- ...
Tradeoffs:
- ...

## Portainer deployment notes
- Stack name: <service>
- Compose path: `<service>/docker-compose.yml`
- Git updates: enabled
- Required variables:
  - `DATA_DIR`
  - `...`

## Optional follow-ups
- [ ] Nginx Proxy Manager hostname
- [ ] Authentik provider/forward-auth
- [ ] API key for Hermes

## Validation
- [ ] `docker compose -f <service>/docker-compose.yml config`
- [ ] `git diff --check`
- [ ] Diff reviewed for secrets/topology
```

## Step 5 — Deploy in Portainer

Only after Justin confirms deployment.

Create the stack from Git:

- Repository: this homelab repository.
- Branch/ref: usually `main` after merge.
- Compose path: `<service>/docker-compose.yml` or `<service>/compose.yaml`.
- Git updates: enabled.
- Stack variables: set from `example.env`, with real secrets supplied out of band.

Verify after deployment:

- Stack is Git-backed.
- Git updates are enabled.
- Containers are running/healthy.
- Persistent mounts point to `/opt/stacks/<service>` or the documented path.
- Local service endpoint responds.
- Logs show no boot loop or permission errors.

## Optional Step — Nginx Proxy Manager

Add NPM only if public or friendly-hostname access is requested.

Confirm:

- LAN-only or public.
- Desired hostname.
- Upstream container/host and port.
- SSL requirement.
- Websocket/SSE requirement.
- Authentik gate requirement.

Verify:

- DNS resolves correctly.
- HTTPS works.
- NPM points to the right upstream.
- Service works from browser.

## Optional Step — Authentik

Prefer native OIDC/OAuth/SAML if the service supports it. Use NPM/Authenik forward-auth if the service lacks good native auth.

Verify:

- Provider/application exists.
- Redirect URI matches the public hostname.
- Login works.
- Logout behavior is acceptable.
- Changes are scoped to this service only.

## Optional Step — API Key for Agents

Only create an API key when explicitly requested or required for an integration.

Flow:

1. Identify minimum permissions.
2. Prefer read-only/scoped token.
3. Store in `pass`, for example:

```bash
pass insert infra/<service>/api-token
# or
pass insert mcp/<service>/api-token
```

4. Verify with a minimal read-only API call.
5. Do not print or commit the token.

## Rollback Checklist

If a deployment fails or is abandoned:

- Remove the Portainer stack, if created.
- Remove dedicated NPM proxy host, if created.
- Remove dedicated Authentik app/provider/outpost entry, if created.
- Remove dedicated DNS record, if created.
- Remove dedicated API key from `pass`, if created.
- Remove dedicated host data path only after explicit confirmation.
- Preserve shared services, shared networks, shared outposts, and unrelated DNS.
