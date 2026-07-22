# Papatenko's Homelab

## Usage

### .env

Rename `example.env` to `.env` in any service directory and change variables for your setup.

### Agent-readable workflows

- **docs/agent-service-onboarding.md** — workflow for adding new services at the repo root through upstream Compose discovery, PRs, Portainer Git stacks, optional NPM/Auth, and optional API keys.
- **docs/repo-organization-plan.md** — long-term proposal for services, infrastructure, automation, templates, inventories, and runbooks; not part of normal service onboarding.
- **docs/storage-layout.md** — persistent data conventions for Portainer Git stacks.

### Stacks

- **media-stack/** — qBittorrent + Jellyfin + Sonarr + Radarr + Prowlarr + Bazarr on a shared network.
- **openwebui/** — Open WebUI + SearXNG + Valkey + Tika + ChromaDB for AI chat with web search and RAG.
- **whisper/** — Self-hosted OpenAI Whisper speech-to-text API using the small model by default.
- **motioneye/** — motionEye camera monitoring and motion detection stack for the Raspberry Pi.
- **opendesign/** — Open Design web UI/API for agent-native design artifacts.
- **wallos/** — Wallos personal subscription tracker.
- **canvas-todoist/** — Hourly sync of UH Canvas assignments into Todoist via the Canvas calendar feed.
- **authentik/** — Authentik identity provider for SSO.
- **nextcloud-mcp/** — Nextcloud MCP server (110+ tools) over streamable-HTTP at `/mcp` for remote MCP clients (Claude, ChatGPT). Fronted by nginxproxymanager.
- **termix/** — Termix browser-based SSH and remote desktop management.
