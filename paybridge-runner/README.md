# paybridge-runner

Self-hosted GitHub Actions runner for `momenta-fire/paybridge`, deployed as a Portainer Git stack.

## Why this exists

PayBridge's `deploy.yml` kept failing with "Artifact storage quota has been hit" — GitHub's 500MB Actions artifact/package storage is shared across every private repo on the account, not per repo. The workflow itself was changed to stop needing that storage (its `build` and `deploy` jobs were merged into one, so the release bundle never leaves the runner's disk). This runner exists to execute that merged `build-and-deploy` job — it's requested for cost/control, independent of the quota fix.

## Compose source

- Runner image: `myoung34/github-runner` — https://github.com/myoung34/docker-github-actions-runner
- `RUNNER_SCOPE: repo`, registered directly against `momenta-fire/paybridge` (a personal account, not an org, so there's no org-wide runner pool to join).
- `ACCESS_TOKEN` is a GitHub PAT, not a manually-pasted registration token: the image uses it to fetch its own registration token on every start, so nothing expires on you between deploys.
- `EPHEMERAL: "1"` — the container deregisters and exits after each job; `restart: unless-stopped` brings it back up fresh and re-registers before the next job. This is the image's documented pattern for Compose and avoids any workspace state carrying over between runs.

## Required Portainer variables

Copy `example.env` into the Portainer stack environment and set at minimum:

- `DATA_DIR` — persistent root for the runner's work directory.
- `GH_RUNNER_PAT` — a GitHub PAT (classic `repo` scope, or fine-grained with Administration read/write) belonging to an account that admins `momenta-fire/paybridge`. GitHub does not allow minting this via API — generate it manually at https://github.com/settings/tokens and store it in the `hermes-agent` Bitwarden Secrets Manager project or directly as this Portainer stack's variable. Do not commit a real value.

## Verification

After deploying, confirm in GitHub → `momenta-fire/paybridge` → Settings → Actions → Runners that `paybridge-runner-services` shows **Idle**. If it doesn't appear, check the container logs for a registration error (most commonly an expired/invalid PAT).

## Rotating the PAT

Generate a new PAT, update the value in Portainer's stack environment (or BWS), then redeploy the stack — the running container picks up the new token on its next restart/registration cycle.
