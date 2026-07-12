# Plan: Organize This Homelab Repository

This is an agent-readable plan for evolving the repository structure without breaking live Portainer stacks.

## Goal

Make the repo easier for humans and agents to navigate by separating deployable services, shared infrastructure, automation, documentation, templates, inventories, and archives.

## Recommended Final Shape

```text
services/                  # deployable application stacks
infrastructure/            # shared platform docs and config contracts
automation/                # operational jobs that run the homelab
scripts/                   # repo validation and developer helpers
templates/                 # boilerplate for new services and PRs
inventories/               # sanitized machine-readable inventories
docs/runbooks/             # cross-service procedures
archive/                   # retired services and migration notes
.github/                   # CI and PR templates
```

## Why This Shape

- `services/`: things Portainer deploys.
- `infrastructure/`: things services depend on, such as proxy, identity, DNS, networks, storage, backups, and monitoring.
- `automation/`: jobs that change, check, or maintain the homelab.
- `scripts/`: helpers for validating this repo.
- `templates/`: starting points for future services.
- `inventories/`: machine-readable service/host/port/domain data.
- `docs/runbooks/`: reusable operating procedures.
- `archive/`: retired stacks and migration records.

Organize by **operational responsibility**, not by tool. Portainer is the deployer, but services should still be services.

## Current-State Note

The repo currently keeps service directories at the root, for example:

```text
actual/
authentik/
backrest/
homepage/
immich/
nginxproxymanager/
whisper/
```

That convention is workable short-term. A move to `services/` should happen gradually because Portainer stack compose paths must be updated after each move.

## Target Directory Details

### `services/`

```text
services/<service>/
  docker-compose.yml
  example.env
  README.md
  config/          # optional non-secret config
  init/            # optional init scripts
```

Rules:

- One deployable service or stack per directory.
- Compose file is the Portainer source.
- `example.env` documents variables only.
- README explains upstream, host placement, Portainer variables, persistence, proxy/auth/API notes, validation, and rollback.

### `infrastructure/`

```text
infrastructure/
  portainer/
  nginx-proxy-manager/
  authentik/
  dns/
  networks/
  storage/
  backup/
  monitoring/
```

Use for shared platform docs and conventions. If one of these has a deployable Compose stack, the stack can live under `services/<name>/` while shared policy docs live under `infrastructure/<name>/`.

### `automation/`

```text
automation/
  maintenance/
  backups/
  healthchecks/
  deployments/
  agent-workflows/
```

Use for jobs that operate the homelab. Scripts here should document credentials, schedule, host context, and rollback behavior.

### `scripts/`

```text
scripts/
  validate-compose.sh
  scan-secrets.sh
  lint-yaml.py
```

Use for repo validation and developer helpers. Difference from `automation/`: `scripts/` checks the repo; `automation/` operates the homelab.

### `templates/`

```text
templates/
  service/
    docker-compose.yml
    example.env
    README.md
  pr-bodies/
    add-service.md
    infrastructure-change.md
```

Use as starter material for new PRs.

### `inventories/`

```text
inventories/
  hosts.example.yaml
  services.yaml
  ports.yaml
  domains.example.yaml
  portainer-stacks.yaml
```

Prefer sanitized `.example.yaml` files for host/domain data unless the repo intentionally stores real private topology.

### `docs/runbooks/`

```text
docs/runbooks/
  add-service.md
  rollback-service.md
  expose-service-with-npm.md
  add-authentik-provider.md
  create-agent-api-key.md
```

Use for procedures that apply across services.

## Migration Phases

### Phase 1 — Add Guardrails Without Moving Live Stacks

- Add `docs/agent-service-onboarding.md`.
- Add this organization plan.
- Add templates for new services.
- Add validation scripts.
- Add a PR template.

Risk: low.

### Phase 2 — Add CI

- Validate YAML.
- Run `docker compose config` for changed Compose files where Docker is available.
- Run secret scanning.
- Run `git diff --check`.

Risk: low to medium if existing files trip new checks.

### Phase 3 — Move Services Gradually

For each service:

1. Create `services/<service>/`.
2. Move files with `git mv`.
3. Add/update README and `example.env`.
4. Validate Compose.
5. Merge PR.
6. After confirmation, update the Portainer stack compose path.
7. Verify Git updates and service health.

Do not move every live stack in one PR unless there is a maintenance window and rollback plan.

### Phase 4 — Consolidate Infrastructure Docs

Move proxy, Authentik, DNS, network, storage, backup, and monitoring docs into `infrastructure/`. Cross-link from service READMEs.

### Phase 5 — Consolidate Automation

Move operational jobs to `automation/` and repo-validation helpers to `scripts/`.

## PR Breakdown

1. **Docs and templates PR** — low risk.
2. **Validation CI PR** — low/medium risk.
3. **One service move PR at a time** — medium risk because Portainer paths change.
4. **Infrastructure docs PR** — low risk.
5. **Automation cleanup PR** — medium risk if active jobs reference paths.

## Validation Checklist

Before merging a repo organization PR:

- [ ] No secrets in diff.
- [ ] No unintended LAN IPs/private domains in public docs.
- [ ] Compose files render or limitation is documented.
- [ ] Moved services have README and `example.env`.
- [ ] Portainer path updates are listed as post-merge tasks.
- [ ] Rollback steps are documented.

After moving any live service:

- [ ] Portainer stack points to the new Git path.
- [ ] Git updates remain enabled.
- [ ] Containers are healthy.
- [ ] Persistent mounts still point to stable host paths.
- [ ] NPM/Auth/API integrations still work.

## Suggested Near-Term Decision

Keep existing root-level service directories for now. Start applying the new workflow to future services and add templates/CI first. Once the conventions are stable, move existing services under `services/` one at a time.
