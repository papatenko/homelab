# PR-Agent GitHub App

Self-hosted, open-source PR-Agent on the Services Docker host, deployed through a Portainer **Git-backed stack** with this directory as the Compose path. This service complements OpenHands; it does not replace it. Image `pragent/pr-agent:0.47.0-github_app` is pinned to the upstream multi-platform digest in `docker-compose.yml` (Linux amd64 and arm64).

**Status:** configuration only. Do not deploy or publish ingress until the GitHub App, webhook ingress, and OmniRoute credential are ready. A healthy container alone does not verify integration.

## Portainer stack variables

Set all of these in Portainer when creating the Git stack. No host-side files, no mounted secrets directory, no SSH into Services required. Every value stays inside Portainer's encrypted variable store.

| Variable | Required | Description |
|---|---|---|
| `PR_AGENT_GITHUB_APP_ID` | Yes | Numeric GitHub App ID (visible on the App settings page, not a secret) |
| `PR_AGENT_GITHUB_PRIVATE_KEY` | Yes | Full PEM private key generated from the GitHub App settings page. Include the `-----BEGIN RSA PRIVATE KEY-----` header and footer with literal newlines. |
| `PR_AGENT_GITHUB_WEBHOOK_SECRET` | Yes | The random secret string you enter both in Portainer and in the GitHub App webhook settings. Webhooks with a missing or wrong signature are rejected with HTTP 403. |
| `PR_AGENT_OPENAI_KEY` | Yes | OmniRoute API key (gateway credential, not a consumer ChatGPT/Codex password). |
| `PR_AGENT_OPENAI_API_BASE` | Yes | OmniRoute OpenAI-compatible API base URL, e.g. `http://192.168.0.X:PORT/v1`. Keep this on the private LAN; do not expose it publicly. |
| `PR_AGENT_MODEL` | Yes | OmniRoute model ID with the `openai/` prefix, e.g. `openai/gpt-5.6-terra`. |
| `PR_AGENT_BIND_ADDRESS` | No | Host bind IP; default `127.0.0.1` for a proxy on the same host. |
| `PR_AGENT_PORT` | No | Host port; default `3110`. |

The PEM key is multi-line. Portainer's stack variable editor accepts literal newlines in values: paste the full PEM block exactly as downloaded from GitHub.

## GitHub App registration

1. Go to **GitHub Settings > Developer settings > GitHub Apps > New GitHub App**.
2. Set the **Webhook URL** to `https://<your-public-domain>/api/v1/github_webhooks` (configure this after the reverse proxy is in place).
3. Set a strong random **Webhook secret** and copy it; you will enter the same string in Portainer as `PR_AGENT_GITHUB_WEBHOOK_SECRET`.
4. **Permissions (Repository):** Pull requests: Read & write; Contents: Read; Issues: Read & write (for issue comment events).
5. **Subscribe to events:** Pull request; Issue comment; Pull request review comment.
6. **Installation:** choose "Only on this account" and install on selected repositories only. Start with one test repo.
7. After creation, download the **private key** PEM from the App settings page. Copy the entire file contents (header, body, footer) into Portainer as `PR_AGENT_GITHUB_PRIVATE_KEY`.
8. Note the **App ID** (shown at the top of the App settings page) and enter it as `PR_AGENT_GITHUB_APP_ID`.

## Reverse proxy (NPM)

Expose **only** `POST /api/v1/github_webhooks` publicly over HTTPS. GitHub must reach this URL; OmniRoute does not need public exposure.

- Upstream: `http://services-host:3110` (or the configured `PR_AGENT_PORT`).
- Deny or 404 all other paths and methods at the proxy level.
- The webhook endpoint validates the HMAC-SHA256 signature automatically; an incorrect or missing secret returns HTTP 403 before any model call is made.

## Deployment checklist

- [ ] GitHub App registered, private key and webhook secret stored in Portainer variables.
- [ ] OmniRoute API key and model ID confirmed and stored in Portainer variables.
- [ ] NPM proxy configured with HTTPS, routing only `POST /api/v1/github_webhooks` to `services-host:3110`.
- [ ] PR merged to `main`; Portainer Git stack created targeting `pr-agent/` on `main`.
- [ ] Container starts healthy (`GET /` returns 200).
- [ ] Test: send a webhook with a wrong secret, verify HTTP 403 rejection.
- [ ] Test: open a harmless PR in the selected test repo, verify PR-Agent posts a `/review` comment.
- [ ] If anything fails: disable GitHub App webhook delivery in GitHub App settings, remove the NPM proxy route, and stop the Portainer stack. No data volume to protect; variables remain in Portainer for later recovery.

## Rollback

Stop the Portainer stack and remove the NPM proxy forward. No persistent data volumes are used. To retire permanently, also delete or suspend the GitHub App in GitHub settings and remove the Portainer stack variables.
