# Course RAG Sync MCP bridge

The approved runtime hostname is `webuikb.papatenko.org`, with MCP path `/mcp`.
Supply the hostname through `RAG_SYNC_MCP_ALLOWED_HOST` at deployment, not as a
portable source default. This name does not expand the four-course allowlist.

Run exactly one replica and one Uvicorn worker. A background monitor reconciles
active jobs every five seconds, even after the initiating client disconnects.
All tool calls and monitor updates share a state lock. Before triggering a job,
the bridge rejects observed upstream activity across all sources. Accepted
dispatches are limited to one per 60 seconds for the shared bridge credential;
polling status remains available. A failed POST may still have started a job,
so ambiguous dispatch failures retain ownership until fresh completion is
observed. Only an explicit `triggered: false` releases a rejected dispatch.
Recovery from unverifiable completion remains operator-controlled: confirm
upstream idle before restarting. Do not clear ownership on a wall-clock timeout.

The bridge cannot prevent independent upstream schedulers from starting jobs
after its preflight; deployment must reconcile those writers before claiming
global upstream serialization. This version uses one shared client credential,
not separately enrolled device credentials.

Staged, not deployed. Stateless Streamable HTTP MCP exposes only `sync_knowledge_base(collection)` and `get_sync_status(collection)` for four fixed course aliases. Requests use a dedicated bearer token from `BRIDGE_TOKEN_FILE`; the upstream token from `OIKB_TOKEN_FILE` stays inside the private network. `/mcp` requires JSON/SSE Accept headers. No source path, KB UUID, or arbitrary upstream URL is accepted from clients.

`POST /sync/{alias}` is asynchronous. Poll the normalized status to terminal. The lock stays held until a fresh terminal observation; a stale terminal snapshot does not count. Pending ownership is persisted in the dedicated `rag-sync-mcp-state` volume so a restart cannot silently clear it. If status cannot be disambiguated, fail closed and investigate rather than claiming completion. An operator must inspect upstream state and the persisted record before recovery. Current tests model the upstream repository's response shape, not a confirmed deployed image digest.

Before deployment: verify the live oikb API and aliases, configure an exact `RAG_SYNC_MCP_ALLOWED_HOST`, and bind only the bridge to the private NAS address with an allowlisted reverse-proxy source. The two Docker endpoints cannot share this bridge network. Portainer's checked-out Git stack has not been proven to include the Docker build context; build from this repository in reviewed CI or on the NAS, push to a private registry, and set `RAG_SYNC_MCP_IMAGE` to an immutable image digest before Git-backed redeploy. Establish BWS-backed secret files and approve the GitOps change. `oikb` must not receive a host port. Run `python -m unittest discover -s . -p 'test*.py' -v` here and Compose config with non-secret placeholders. No production registration until end-to-end checks pass.
