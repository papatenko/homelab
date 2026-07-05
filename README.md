# Papatenko's Homelab

## Usage

### .env

Rename `example.env` to `.env` in any service directory and change variables for your setup.

### Stacks

- **media-stack/** — qBittorrent + Jellyfin + Sonarr + Radarr + Prowlarr + Bazarr on a shared network.
- **openwebui/** — Open WebUI + SearXNG + Valkey + Tika + ChromaDB for AI chat with web search and RAG.
- **wallos/** — Wallos personal subscription tracker.
- **canvas-todoist/** — Hourly sync of UH Canvas assignments into Todoist via the Canvas calendar feed.
- **authentik/** — Authentik identity provider for SSO.
