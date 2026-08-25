---
name: custom-docker-service
description: Use when adding a homelab service (via docs/agent-service-onboarding.md) whose upstream project has no official Docker image, Dockerfile, or compose file — a CLI tool, npm/pip package, or desktop app you need to containerize yourself. Covers verifying no image exists, finding the tool's real self-hosted serve mode instead of guessing, writing a from-source Dockerfile, and the bind-address / permission / PID-namespace pitfalls that only show up once you actually run the container.
---

# Containerizing a service with no official Docker image

This extends `docs/agent-service-onboarding.md` for the case where Step 1
("Find the Upstream Docker Compose") comes up empty. Do the checks below
*before* writing any Dockerfile — most "let's just containerize the CLI"
tasks are either a five-minute job or a bad idea, and you can't tell which
without checking.

## 1. Prove there's really no image

Don't start writing a Dockerfile on the assumption that one doesn't exist —
verify it, and record what you checked in the PR body:

```bash
gh api repos/<owner>/<repo>/contents          # look for Dockerfile / compose.yaml / .yml
gh api repos/<owner>/<repo>/packages          # GitHub Container Registry
gh release list -R <owner>/<repo>             # release assets sometimes include one
curl -s "https://hub.docker.com/v2/search/repositories/?query=<name>"
```

If any of these turn something up, use it — don't reinvent an image the
maintainer already publishes.

## 2. Find the tool's real "run as a server" mode — don't guess

Read the upstream `README.md` / `CLAUDE.md` / `AGENTS.md` / `docs/` before
writing anything. Look specifically for:

- A `serve` / `start` / `daemon` subcommand, not just a one-shot CLI.
- What port/interface it binds by default, and whether that's configurable.
- Where it writes persistent state (so you know what to volume-mount).
- Whether the tool syncs to a *hosted service the maintainer owns* — if so,
  self-hosting it only gets you the local half; say that explicitly rather
  than implying full feature parity with the hosted product.

If there's no server mode at all — the tool is purely a local CLI or desktop
app meant to run on the user's own machine — that's a real finding, not a
blocker to work around. Surface it (AskUserQuestion, in plan mode) instead of
forcing a container that doesn't match how the tool is designed to be used.

## 3. Write the Dockerfile against this repo's existing conventions

Same shape as any other service in this repo (see `opendesign/` as the
reference `docker-compose.yml`/`example.env`/`README.md` layout) — the only
difference is `build: .` instead of `image: <upstream>`. Pin the base image
tag, install via the package manager the project actually publishes to (npm,
pip, etc.), and don't add anything beyond what's needed to run the server
mode found in step 2.

## 4. Pitfalls that only surface at `docker run`, not at `docker build`

These bit us building `tokentracker/` — a Node CLI (`tracker serve`) with no
official image. All three passed a clean build and only failed once actually
started:

- **Hardcoded loopback bind.** Some local-first CLIs bind `127.0.0.1` with no
  `--host` flag or env override, because they were designed to run on a
  developer's own machine, not to be reverse-proxied. A published Docker port
  won't reach that. Fix: run the process in the background and forward the
  container's public interface to it with `socat TCP-LISTEN:$PORT,fork,reuseaddr
  TCP:127.0.0.1:$PORT` in the entrypoint — don't patch the app.
- **Bind-mounted volumes arrive owned by the host UID**, not whatever
  non-root user your image runs as. If the Dockerfile drops to `USER
  <app>` before the volume is ever written, permission errors on data-dir
  init will look like an app bug. Fix: start the container as root, `chown
  -R` the mounted data dir in the entrypoint, then re-exec as the
  unprivileged user with `su-exec` (Alpine) or `gosu` (Debian) — don't run
  the whole container as root.
- **Don't trust the app's own "kill whatever's using this port" logic
  inside a container.** If a CLI shells out to `lsof`/`fuser` to free its
  port before binding, the pids it finds can be meaningless or dangerous
  inside a container's PID namespace (observed: it returned pid 1 — the
  container's own init — and killed it, taking the whole container down).
  If passing an explicit `--port` or `$PORT` flips this behavior on, prefer
  leaving the tool on its own default port and discovering what it actually
  chose (parse it from the startup log) rather than forcing a value.
- **Some tools change their own default port based on kernel detection**
  (e.g. checking `/proc/version` for a WSL2 host and picking a different
  port to dodge a Windows-side service). A container inherits the host
  kernel's `/proc/version`, so this can trigger identically inside Docker.
  Don't hardcode the expected port anywhere downstream (healthcheck, socat
  target) — discover it at runtime the same way, from the process's own
  output, so the setup works regardless of which port it lands on.

## 5. Verify for real before calling it done

`docker compose config` only proves the YAML parses — it proves nothing about
runtime behavior. Actually build and run it:

```bash
docker compose -f <service>/docker-compose.yml build
docker compose -f <service>/docker-compose.yml up -d
docker logs <container>                 # watch for permission errors, crash loops
curl -sf http://localhost:<published-port>/
docker inspect --format='{{.State.Health.Status}}' <container>
```

Then tear the test container/image down — this is local verification, not
part of the repo's committed state.

## 6. Flag scope limits explicitly, don't bury them

If the self-hosted container only replicates *part* of what the tool does
when run natively (e.g. it needs live OAuth credential files or per-host log
directories to be useful, and won't aggregate data from other machines on
its own), say so in the service's `README.md` and the PR's "Deployment fit"
section. Any bind-mount of live credentials or another host's data is a real
access grant — call it out and get explicit confirmation before wiring it up,
per the safety rules in `docs/agent-service-onboarding.md`.
