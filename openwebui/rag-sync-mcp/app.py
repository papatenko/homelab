import hmac
import os
import threading
from pathlib import Path
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route
from starlette.types import ASGIApp, Receive, Scope, Send

ALIASES = frozenset({"cosc-4337", "cosc-4351", "cosc-4397", "mark-3336"})

class BearerAuthMiddleware:
    def __init__(self, app: ASGIApp, token: str): self.app, self.token = app, token
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope.get("path", "").startswith("/mcp"):
            headers = dict(scope.get("headers", [])); auth = headers.get(b"authorization", b"").decode("latin1")
            supplied = auth[7:] if auth.startswith("Bearer ") else ""
            if not self.token or not hmac.compare_digest(supplied.encode(), self.token.encode()):
                response = JSONResponse({"error": "unauthorized"}, status_code=401)
                await response(scope, receive, send); return
        await self.app(scope, receive, send)

class Bridge:
    def __init__(self, upstream: str, upstream_token: str, client: Any | None = None):
        self.upstream = upstream.rstrip("/"); self.upstream_token = upstream_token
        self.client = client or httpx.Client(timeout=httpx.Timeout(5.0, connect=2.0), follow_redirects=False)
        self.lock = threading.Lock()
        self.active_alias: str | None = None
        self.baseline_sync: int | float | None = None
        self.seen_running = False
    def _request(self, method: str, path: str) -> dict[str, Any]:
        try:
            response = self.client.request(method, f"{self.upstream}{path}",
                headers={"Authorization": f"Bearer {self.upstream_token}"})
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict): raise ValueError("bad upstream response")
            return data
        except Exception:
            raise RuntimeError("Sync service unavailable") from None
    def _status(self, alias: str) -> dict[str, Any]:
        data = self._request("GET", "/health")
        sources = data.get("sources")
        if not isinstance(sources, dict): raise RuntimeError("Sync service unavailable")
        rows = [row for key, row in sources.items() if isinstance(row, dict)
                and (key == alias or row.get("name") == alias)]
        if len(rows) != 1:
            return {"collection": alias, "state": "unknown"}
        row = rows[0]
        raw = row.get("status")
        mapping = {"running": "running", "success": "success", "partial": "failed",
                   "error": "failed", "failed": "failed", "cancelled": "failed", "idle": "idle"}
        state = mapping.get(raw, "unknown") if isinstance(raw, str) else "unknown"
        result: dict[str, Any] = {"collection": alias, "state": state}
        if isinstance(row.get("last_sync"), (int, float)):
            result["last_sync_at"] = row["last_sync"]
        counts = (row.get("files_added"), row.get("files_modified"), row.get("files_deleted"))
        if all(isinstance(n, int) and n >= 0 for n in counts): result["changed"] = sum(counts)
        if state == "failed": result["error_class"] = "sync_failed"
        return result
    def invoke(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(args, dict) or set(args) != {"collection"}: raise ValueError("invalid arguments")
        alias = args["collection"]
        if not isinstance(alias, str) or alias not in ALIASES: raise ValueError("invalid collection")
        if name == "get_sync_status":
            result = self._status(alias)
            if alias == self.active_alias and result["state"] in {"success", "failed"}:
                fresh = self.seen_running or (isinstance(result.get("last_sync_at"), (int, float))
                        and result["last_sync_at"] != self.baseline_sync)
                if not fresh:
                    result = {"collection": alias, "state": "unknown"}
                else:
                    self.active_alias = None
                    self.seen_running = False
                    self.baseline_sync = None
                    if self.lock.locked(): self.lock.release()
            elif alias == self.active_alias and result["state"] == "running":
                self.seen_running = True
            return result
        if name != "sync_knowledge_base": raise ValueError("unknown tool")
        if not self.lock.acquire(blocking=False):
            return {"accepted": False, "collection": alias, "operation": "sync", "status": "busy"}
        try:
            before = self._status(alias)
            self.baseline_sync = before.get("last_sync_at")
            self.seen_running = False
            result = self._request("POST", f"/sync/{alias}")
            if result.get("triggered") is not True or result.get("name") != alias:
                raise RuntimeError("Sync service unavailable")
            self.active_alias = alias
            return {"accepted": True, "collection": alias, "operation": "sync", "status": "accepted"}
        except Exception:
            self.lock.release()
            raise

def create_app(bridge: Bridge, bearer_token: str) -> Starlette:
    allowed_host = os.environ.get("MCP_ALLOWED_HOST", "").strip()
    mcp = FastMCP("course-rag-sync", stateless_http=True, json_response=True,
                  max_request_body_size=16384,
                  transport_security=TransportSecuritySettings(
                      allowed_hosts=["localhost", "localhost:*", "127.0.0.1:*", "rag-sync-mcp:*", *([allowed_host] if allowed_host else [])],
                      allowed_origins=[]))
    @mcp.tool()
    def sync_knowledge_base(collection: str, **extra: Any) -> dict[str, Any]:
        """Synchronize one approved course knowledge base."""
        return bridge.invoke("sync_knowledge_base", {"collection": collection, **extra})
    @mcp.tool()
    def get_sync_status(collection: str) -> dict[str, Any]:
        """Get normalized sync status for one approved course knowledge base."""
        return bridge.invoke("get_sync_status", {"collection": collection})
    async def healthz(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})
    app = mcp.streamable_http_app()
    app.routes.insert(0, Route("/healthz", healthz))
    app.add_middleware(BearerAuthMiddleware, token=bearer_token)
    app.state.mcp_server = mcp
    return app

def read_secret(name: str) -> str:
    value = Path(os.environ[name]).read_text(encoding="utf-8").strip()
    if not value: raise RuntimeError(f"empty required secret file: {name}")
    return value

def main() -> None:
    import uvicorn
    bridge = Bridge(os.environ.get("OIKB_URL", "http://oikb:8080"), read_secret("OIKB_TOKEN_FILE"))
    uvicorn.run(create_app(bridge, read_secret("BRIDGE_TOKEN_FILE")), host="0.0.0.0", port=8000)

if __name__ == "__main__": main()
