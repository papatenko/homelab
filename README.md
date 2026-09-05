# Papatenko's Homelab

## Usage

### .env

Rename `example.env` to `.env` in any service directory and change variables for your setup.

### Agent-readable workflows

- **docs/agent-service-onboarding.md** — workflow for adding new services at the repo root through upstream Compose discovery, PRs, Portainer Git stacks, optional NPM/Auth, and optional API keys.
- **docs/repo-organization-plan.md** — long-term proposal for services, infrastructure, automation, templates, inventories, and runbooks; not part of normal service onboarding.
- **docs/storage-layout.md** — persistent data conventions for Portainer Git stacks.

### Homepage layout convention

Every Homepage section must be declared in `homepage/config/settings.yaml` with
`style: row` and an explicit column count. Use four columns by default so new
sections match the existing dashboard layout. Keep the embedded `services.yaml`
and `settings.yaml` blocks in `homepage/docker-compose.yaml` synchronized with
their standalone files. Service cards should use a concise label, icon, `href`,
and `siteMonitor`; omit descriptions unless they convey essential information
that the label cannot. Never commit literal LAN IP addresses in Homepage or
other homelab configuration. Add or reuse a deployment variable such as
`HOMEPAGE_VAR_*`, and keep the real address only in Portainer or the applicable
runtime environment.

### Stacks

- **media-stack/** — qBittorrent + Jellyfin + Sonarr + Radarr + Prowlarr + Bazarr on a shared network.
- **openwebui/** — Open WebUI + SearXNG + Valkey + Tika + ChromaDB for AI chat with web search and RAG.
- **whisper/** — Self-hosted OpenAI Whisper speech-to-text API using the small model by default.
- **neutts/** — GPU-backed, on-device NeuTTS-2E API for local speech synthesis.
- **motioneye/** — motionEye camera monitoring and motion detection stack for the Raspberry Pi.
- **wallos/** — Wallos personal subscription tracker.
- **canvas-todoist/** — Hourly sync of UH Canvas assignments into Todoist via the Canvas calendar feed.
- **authentik/** — Authentik identity provider for SSO.
- **nextcloud/** — Nextcloud All-in-One instance, with a co-located Nextcloud MCP server (110+ tools) over streamable-HTTP at `/mcp` for remote MCP clients (Claude, ChatGPT). Fronted by nginxproxymanager.
- **termix/** — Termix browser-based SSH and remote desktop management.
- **n8n/** — n8n workflow automation stack.
