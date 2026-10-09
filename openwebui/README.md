# Open WebUI, bounded Obsidian RAG pilot

This is a Portainer Git-stack definition for the NAS-hosted, CPU-first Open WebUI pilot. It intentionally replaces the previous generic web-search stack. It does not deploy itself, create a knowledge base, ingest a file, or expose a public endpoint.

## Non-negotiable properties

- Obsidian is canonical. Open WebUI state under `/mnt/misc/open-webui/` is disposable and rebuildable.
- `oikb` sees only the single, explicitly approved pilot directory mounted as `/source:ro`.
- The stack has no host networking, no Docker socket, no generic outbound tool configuration, no local LLM, and no embedded real-world topology.
- Open WebUI deliberately tracks the upstream `main` container tag at Justin's request, so Portainer pulls current upstream images during an approved redeploy. `oikb` deliberately tracks the upstream `latest` image alongside Open WebUI, per Justin's rolling-image policy.
- The `oikb` API endpoints are internal-only. Its two API keys are mounted from runtime secret files, never committed.

## Search and vector-store decisions

- SearXNG is deliberately deferred from this bounded RAG pilot. It solves public-web discovery, not private-vault retrieval, and adds outbound-query, web-loader, engine-maintenance, and policy concerns. Add it later as a separate internal-only service only after vault-only retrieval is validated.
- A separate Chroma service is deliberately deferred. Open WebUI's persisted embedded Chroma store is the documented simple single-process topology and is adequate for the 50 to 150 note pilot. Reassess an external vector store only for multi-worker/replica operation or measured retrieval/sync bottlenecks.

## Image update policy

Open WebUI uses `ghcr.io/open-webui/open-webui:main` intentionally. This is a user-directed rolling update policy, not an accidental unpinned reference. Review release notes and back up the derived data root before any Portainer image update/redeploy. The stack is not configured for Watchtower and has no automated redeploy rule.

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

## Local embedding runtime

The current upstream Open WebUI image selects its built-in SentenceTransformers implementation when `RAG_EMBEDDING_ENGINE` is empty. Do not set it to `sentence_transformers`, which current upstream releases reject as an unknown engine. The model remains `sentence-transformers/all-MiniLM-L6-v2`.

## Runtime port and synchronizer

Use a private host port that does not conflict with existing NAS services. The current NAS deployment uses port `3000`. The `oikb` image entrypoint is `oikb`, so Compose must supply `command: daemon` to keep the scheduled synchronizer running.

## oikb configuration mount

The oikb daemon reads its default configuration from `/app/.oikb.yaml`; mount the protected host-side generated configuration there. Mounting it at `/data/.oikb.yaml` leaves the daemon with no configured sources.

## oikb healthcheck

The rolling oikb image does not include `wget`. Its healthcheck uses the image’s bundled Python runtime to request `/health/ready` instead.

## Private host publication

Open WebUI publishes only its explicitly configured private host binding. The shared application network must not use Docker `internal: true`, because Docker suppresses host port publication for a container attached only to an internal network. oikb remains un-published and is reachable only by the application network.

## oikb API key loading

oikb resolves its own `OIKB_API_KEY` from `OIKB_API_KEY_FILE`, but reads the Open WebUI key only from `OPEN_WEBUI_API_KEY` or its config file. The compose entrypoint therefore exports `OPEN_WEBUI_API_KEY` from the mounted secret immediately before `exec oikb daemon`. The value never appears in the compose file, Portainer variables, or logs.

