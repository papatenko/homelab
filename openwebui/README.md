# Open WebUI, bounded Obsidian RAG pilot

This is a Portainer Git-stack definition for the NAS-hosted, CPU-first Open WebUI pilot. It intentionally replaces the previous generic web-search stack. It does not deploy itself, create a knowledge base, ingest a file, or expose a public endpoint.

## Non-negotiable properties

- Obsidian is canonical. Open WebUI state under `/mnt/misc/open-webui/` is disposable and rebuildable.
- `oikb` sees only the single, explicitly approved pilot directory mounted as `/source:ro`.
- The stack has no host networking, no Docker socket, no generic outbound tool configuration, no local LLM, and no embedded real-world topology.
- The image tags are pinned: Open WebUI `v0.11.4`, `oikb` `v0.5.0`.
- The `oikb` API endpoints are internal-only. Its two API keys are mounted from runtime secret files, never committed.

## Approval gates before deployment

1. Repair and verify NAS backup coverage for `/mnt/misc/open-webui/`. The preflight found the active `rsync-backup.service` failing, so deployment is blocked until the backup owner verifies a successful, restorable run.
2. Select a non-secret pilot directory of roughly 50 to 150 Markdown notes. Set `OBSIDIAN_PILOT_SOURCE_DIR` to that exact NAS-local path, not the whole vault, WebDAV, or FUSE source.
3. Create `/mnt/misc/open-webui/{data,sync-state,logs,backups}` on NAS with the intended service ownership. This is a NAS filesystem change and needs explicit authorization.
4. Deploy through a Git-backed Portainer stack with the environment values above. Bind to the approved private address only.
5. Complete first-run Open WebUI bootstrap, create a dedicated non-admin sync account/API key and the pilot Knowledge Base, then create the runtime `oikb.yaml` from `oikb.example.yaml` using the resulting KB UUID.
6. Put both API values in approved runtime secret files managed through BWS/Portainer. Never put them in `.env`, source control, Obsidian, prompts, or logs.
7. Run initial sync and add/edit/rename/delete/conflict-isolation/citation tests before widening scope.

## Rollback

Stop and remove the Portainer stack. It never writes to the mounted source. Preserve `/mnt/misc/open-webui/` for investigation or restore from the verified backup. Removing that directory is a separate explicit authorization, because it destroys derived data.
