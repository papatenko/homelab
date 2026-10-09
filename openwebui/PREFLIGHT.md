# NAS RAG deployment and rollback preflight

This checklist is the required evidence before an authorized Portainer deployment. It deliberately keeps actual infrastructure details out of the public repository.

## Phase 1, GPU restoration, separate change

The RAG pilot is CPU-first. Do not combine GPU recovery with this stack change.

1. On the Proxmox host, capture the current LXC configuration, GPU device mapping, IOMMU/kernel state, and the target-workload configuration before changing any configuration.
2. Confirm the target guest has the intended device nodes and permissions, then make one approved mapping/driver change in a maintenance window.
3. Verify a real Immich or Nextcloud workload uses acceleration. Device visibility alone is insufficient.
4. Observe stability before relying on acceleration for RAG. Preserve the former LXC configuration as the rollback artifact.

## Phase 2, NAS Open WebUI

### Image updates

Open WebUI and `oikb` intentionally follow their upstream rolling container tags (`main` and `latest`). Before an approved Portainer image update/redeploy, read the upstream release notes, confirm a recent backup of the derived state root, and retain the previously running image digest for rollback. Do not enable unattended Watchtower updates for this stateful service.

### Search and vector-store boundary

This pilot intentionally excludes SearXNG and a standalone Chroma service. SearXNG is a follow-up public-web research capability, with its own outbound-data policy and internal-network isolation requirements. The single-process embedded vector store is the supported low-dependency starting point; add an external store only after measured scaling/concurrency needs justify its additional backup and recovery surface.

1. Confirm the NAS backup job has a recent successful run and a tested restore path covering `/mnt/misc/open-webui/`. The preflight that accompanied this PR found a failing active backup unit, so this is a deployment blocker.
2. Choose a non-secret Markdown-only pilot, about 50 to 150 notes. Configure its exact NAS-local path as `OBSIDIAN_PILOT_SOURCE_DIR`, never the vault root.
3. Confirm that the `oikb` image UID can traverse and read the pilot directory. The mount must stay `:ro`.
4. Create the planned persistent directory tree under `/mnt/misc/open-webui/`, set correct service ownership, and ensure it is included in backup scope. This is an authorized NAS-side filesystem change.
5. Create the Git-backed Portainer stack from this directory. Provide all variables through Portainer. Create no public proxy route at this stage.
6. Bootstrap Open WebUI, create a dedicated non-admin sync user/API key and one pilot Knowledge Base. Place API values only in BWS/Portainer-provided runtime secret files.
7. Create the host-side `oikb.yaml`, replacing only the KB placeholder. Start with six-hour, single-concurrency sync.
8. Validate one initial sync plus add, edit, rename, delete, conflict-copy isolation, citation, restart-persistence, storage-placement, logs, and backup-inclusion tests.

## Rollback

- Stop/remove the Portainer stack. The source mount was read-only, so source notes and Nextcloud sync state remain untouched.
- Preserve `/mnt/misc/open-webui/` for diagnostics or restore it from the verified backup if needed.
- Restore the prior LXC configuration only for a separately authorized GPU change. Do not delete derived RAG data or alter the source corpus as part of rollback without explicit approval.
