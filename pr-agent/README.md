# PR-Agent GitHub App

Self-hosted, open-source PR-Agent on the Services Docker host, deployed through a Portainer **Git-backed stack** with this directory as the Compose path. This service complements OpenHands; it does not replace it. Image `pragent/pr-agent:0.47.0-github_app` is pinned to the upstream multi-platform digest in `docker-compose.yml` (Linux amd64 and arm64).

**Status:** configuration only. Do not deploy or publish ingress until the app, secret, model route, firewall, and review scope are ready. A successful Compose validation is not a successful PR review.

## Portainer runtime variables

Set these on the Services endpoint when creating the Git stack (not in Git or a committed `.env` file):

- `PR_AGENT_CONFIG_DIR`: existing absolute host directory containing `.secrets.toml`, readable by container UID 10001. Example placeholder: `/opt/stacks/pr-agent/config`. Mount is read-only at `/app/pr_agent/settings_prod`, where PR-Agent v0.47.0 loads `.secrets.toml`.
- `PR_AGENT_OPENAI_API_BASE`: the privately reachable OmniRoute OpenAI-compatible API base URL, including its `/v1` path as appropriate. Enter the **actual** private URL only in Portainer.
- `PR_AGENT_MODEL`: an OmniRoute-supported model identifier with the `openai/` prefix, for example `openai/<gateway-model-id>`. Confirm that OmniRoute actually supports this model and the needed chat-completions behavior. No consumer ChatGPT/Codex subscription is assumed to be an unattended API key.
- `PR_AGENT_BIND_ADDRESS`: optional host bind IP. Default `127.0.0.1` allows only a proxy on the same host. If the reverse proxy is on another host, explicitly bind to a Services private interface and firewall the port to the proxy host only.
- `PR_AGENT_PORT`: optional host port, default `3110`. Check conflicts before deploying.

Never enter the API key or GitHub App private key in Portainer stack variables. The host-side `.secrets.toml` must be **provisioned from Bitwarden Secrets Manager at runtime**, not put in Git or Portainer. It must contain this shape with real values supplied securely and appropriate quoting for PEM newlines:

```toml
[github]
app_id = 123456
private_key = """<GitHub App PEM private key>"""
webhook_secret = "<long random GitHub webhook secret>"

[openai]
key = "<OmniRoute-compatible gateway credential>"
```

Provision the host directory as owner UID/GID `10001:10001` with mode `0700` and the file with mode `0400`; do not commit, paste, or log the populated file. Create it atomically from BWS values with restrictive umask, never a world-readable Compose variable or CLI argument. The app ID is not a secret, but this arrangement keeps the entire GitHub identity together. Verify that the Services host can reach the configured private API base without making the gateway public. Rotation means updating the runtime file securely and recreating the stack; rollback means removing ingress and the Git stack while preserving the host-side secrets until explicitly retired.

## GitHub App and webhook

1. After review and merge, create a dedicated GitHub App with **selected repositories only**. Grant the permissions upstream PR-Agent requires for pull request reads/comments, contents reads, and checks only if needed. Subscribe to `Pull request`, `Issue comment`, and `Pull request review comment` events; confirm exact permissions/events in the [upstream GitHub App installation guide](https://qodo-merge-docs.qodo.ai/installation/github/) for the pinned release. Do not install the app broadly for this trial.
2. Create the private key and a strong webhook secret, record them only in BWS, then stage the host-side file above. The configured secret is mandatory: PR-Agent rejects unsigned and incorrectly signed webhooks.
3. On the reverse proxy, expose **only** `POST /api/v1/github_webhooks` over HTTPS to this private upstream. Deny other paths and methods at the proxy; keep `/` health, `/docs`, and other routes private. Enable proxy/request limits and monitor logs without request-body or secret logging. Route the callback only after private bind/firewall validation.
4. In GitHub App settings, point the webhook URL to `https://<approved-public-host>/api/v1/github_webhooks` and set the matching secret. Install on one approved test repository. GitHub must reach this URL; OmniRoute does **not** need public exposure.
5. The stack automatically invokes only `/review` on newly opened/reopened/ready-for-review PRs. Comment commands remain available through the GitHub App. Repository-supplied PR-Agent settings are disabled to keep the trial's model and routing fixed.

## Deployment and verification gate

- Review this PR and merge through the normal Homelab process. Create a **Git-backed** Portainer stack targeting this Compose path on Services; do not manually paste Compose or deploy an unmerged branch.
- Confirm image digest and pull, container health (`GET /` responds), private bind/firewall, and the reverse proxy's rejection of unapproved paths. A healthy container alone does not verify integration.
- First send a webhook with an invalid signature and verify rejection; use GitHub's delivery UI to confirm a valid delivery. Then open a harmless PR in the selected test repository and verify **one** PR-Agent review comment and an actual successful OmniRoute request. Check `/review` comment command. Check that neither sensitive values nor PR content appear in proxy access logs beyond what is necessary.
- If any step fails, disable GitHub App delivery/remove the callback, remove the reverse-proxy route, and roll back the stack. Keep the BWS items for controlled retirement or rotation; do not delete them as an incidental rollback.
