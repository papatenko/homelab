# TokenTracker

Local-first AI coding token usage & cost dashboard for Claude Code, Codex,
Cursor, Gemini, and 30+ other tools.

- Upstream: https://github.com/xiufengsun/TokenTracker
- Package: [`tokentracker-cli`](https://www.npmjs.com/package/tokentracker-cli) (npm)

## Why a custom Dockerfile

TokenTracker ships no official Docker image, `Dockerfile`, or compose file —
it's built as a local CLI (`tracker`) plus native macOS/Windows/Linux desktop
apps. The CLI does have a real self-hostable web server (`tracker serve`,
confirmed via its own `CLAUDE.md`): it serves the built React dashboard and a
local JSON API on port `7680`, reading usage data the CLI parses from AI
coding tool logs on disk.

`tracker serve` hardcodes binding to `127.0.0.1` with no `--host` flag or env
override (`src/commands/serve.js`, `LOCAL_BIND_HOST`), so a bare container
can't publish it. This image runs `tracker serve` in the background and uses
`socat` to forward the container's public interface to that loopback port
(see `entrypoint.sh`).

## Data scope — read before deploying

This is **not** a multi-host aggregator. Two separate limitations:

1. **Token/cost history** only covers AI CLI tools that actually run inside
   this container, or whose log directories are bind-mounted in from
   elsewhere. It will not automatically pick up usage from your other
   machines.
2. **The usage-limits panel** (Claude Code / Codex / Antigravity / Cursor /
   Grok / Qoder / OpenCode Go quota bars) reads each tool's local OAuth
   credential files directly (e.g. `~/.claude`, `~/.codex`) and calls that
   provider's usage API. For those bars to populate, the relevant credential
   directories must be bind-mounted in **read-only** from the host that holds
   them (see the commented volume lines in `docker-compose.yml`). That's a
   real filesystem access grant to live OAuth tokens — only add it with
   Justin's explicit confirmation of the source host and scope, per
   `docs/agent-service-onboarding.md`.

The maintainer's own cloud sync (`tokentracker.cc` / InsForge) is a separate,
unrelated backend; the optional `INSFORGE_*` / `TOKENTRACKER_*_TOKEN` vars in
`example.env` only matter if you want this instance to sync there.

## Persistent data

- `${DATA_DIR:-/opt/stacks/tokentracker}/data` → `/home/tokentracker/.tokentracker`
  (queue, cursors, cache — the tracker's own state).

## Ports / variables

See `example.env`. Default published port: `7680`. The container listens
internally on `8765`, not `7680` — see the comment in `docker-compose.yml`:
some Docker networking configs run a docker-proxy *inside* the container's
own network namespace on the published container port, which collides with
`socat` trying to bind that same port for its loopback forward.

## Build (same workaround as `neutts`)

This stack deliberately separates image construction from service
deployment. Portainer CE's remote agent BuildKit path can be unavailable
even when native Docker builds work correctly on the target host (observed:
`docker compose up --build` over a Portainer git-repository stack fails
listing BuildKit workers with an HTTP/2 frame error).

1. On the target host (Services), build the tagged image from the checked-out
   repository:

   ```bash
   docker compose -f docker-compose.yml -f docker-compose.build.yml build tokentracker
   ```

2. In Portainer, create a Git-backed stack from `tokentracker/docker-compose.yml`
   only. Do **not** add `docker-compose.build.yml` to the stack.

When a Git update changes `Dockerfile`, `entrypoint.sh`, or `run-tracker.sh`,
rebuild the tagged image on the target host before redeploying the stack.

## Validation

```bash
docker compose -f tokentracker/docker-compose.yml -f tokentracker/docker-compose.build.yml config
docker compose -f tokentracker/docker-compose.yml -f tokentracker/docker-compose.build.yml build tokentracker
docker compose -f tokentracker/docker-compose.yml up -d
curl -sf http://localhost:7680/
```

## Rollback

Standard: remove the Portainer stack and `${DATA_DIR}` (only after explicit
confirmation, since it holds tracked usage history).
