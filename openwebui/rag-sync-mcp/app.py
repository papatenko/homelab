import fcntl
import hmac
import json
import os
import threading
import time
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

def acquire_singleton(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        raise RuntimeError("bridge already running") from None
    return handle

def parse_aliases(value: str) -> frozenset[str]:
    parts = value.split(",")
    if any(not part or part.strip() != part for part in parts):
        raise ValueError("invalid alias allowlist")
    return frozenset(parts)

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
    def __init__(self, upstream: str, upstream_token: str, client: Any | None = None,
                 state_path: str | Path | None = None, aliases: frozenset[str] | set[str] = ALIASES):
        if not aliases or any(not isinstance(a, str) or not a or len(a) > 80 or
                              not all(c.isascii() and (c.isalnum() or c in "-_") for c in a)
                              for a in aliases):
            raise ValueError("invalid alias allowlist")
        self.aliases = frozenset(aliases)
        self.upstream = upstream.rstrip("/"); self.upstream_token = upstream_token
        self.client = client or httpx.Client(timeout=httpx.Timeout(5.0, connect=2.0), follow_redirects=False)
        self.lock = threading.Lock()
        self.active_alias: str | None = None
        self.baseline_sync: int | float | None = None
        self.seen_running = False
        self.state_lock = threading.RLock()
        self.running_upstream = False
        self.last_request = float("-inf")
        self.state_path = Path(state_path) if state_path is not None else None
        if self.state_path is not None:
            self._load_state()
    def _save_state(self) -> None:
        if self.state_path is None:
            return
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as output:
            json.dump({"version": 1, "active_alias": self.active_alias,
                       "baseline_sync": self.baseline_sync, "seen_running": self.seen_running}, output)
            output.flush()
            os.fsync(output.fileno())
        os.replace(tmp, self.state_path)
        directory = os.open(self.state_path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    def _load_state(self) -> None:
        if self.state_path is None:
            return
        try:
            state = json.loads(self.state_path.read_text(encoding="utf-8"))
            if not isinstance(state, dict) or state.get("version") != 1:
                raise ValueError("invalid persisted state")
            alias = state.get("active_alias")
            baseline = state.get("baseline_sync")
            if alias is None and baseline is None and state.get("seen_running") is False:
                return
            if alias not in self.aliases or (baseline is not None and (isinstance(baseline, bool) or not isinstance(baseline, (int, float)))):
                raise ValueError("invalid persisted state")
            self.active_alias, self.baseline_sync, self.seen_running = alias, baseline, False
            self.lock.acquire()
        except FileNotFoundError:
            pass
        except Exception:
            self.active_alias = "__unknown_pending__"
            self.lock.acquire()
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
        if not isinstance(sources, dict) or not sources:
            raise RuntimeError("Sync service unavailable")
        valid_states = {"running", "success", "partial", "error", "failed", "cancelled", "idle"}
        if any(not isinstance(row, dict) or row.get("status") not in valid_states
               for row in sources.values()):
            raise RuntimeError("Sync service unavailable")
        self.running_upstream = any(row["status"] == "running" for row in sources.values())
        rows = [row for key, row in sources.items() if isinstance(row, dict)
                and (key == alias or row.get("name") == alias)]
        if len(rows) != 1:
            raise RuntimeError("Sync service unavailable")
        row = rows[0]
        raw = row.get("status")
        mapping = {"running": "running", "success": "success", "partial": "failed",
                   "error": "failed", "failed": "failed", "cancelled": "failed", "idle": "idle"}
        state = mapping.get(raw, "unknown") if isinstance(raw, str) else "unknown"
        if state == "unknown":
            raise RuntimeError("Sync service unavailable")
        result: dict[str, Any] = {"collection": alias, "state": state}
        if isinstance(row.get("last_sync"), (int, float)):
            result["last_sync_at"] = row["last_sync"]
        counts = (row.get("files_added"), row.get("files_modified"), row.get("files_deleted"))
        if all(isinstance(n, int) and n >= 0 for n in counts): result["changed"] = sum(counts)
        if state == "failed": result["error_class"] = "sync_failed"
        return result
    def reconcile(self) -> None:
        with self.state_lock:
            if self.active_alias in self.aliases:
                self._invoke("get_sync_status", {"collection": self.active_alias})

    def invoke(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        with self.state_lock:
            return self._invoke(name, args)

    def _invoke(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(args, dict) or set(args) != {"collection"}: raise ValueError("invalid arguments")
        alias = args["collection"]
        if not isinstance(alias, str) or alias not in self.aliases: raise ValueError("invalid collection")
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
                    self._save_state()
            elif alias == self.active_alias and result["state"] == "running":
                self.seen_running = True
            return result
        if name != "sync_knowledge_base": raise ValueError("unknown tool")
        if self.active_alias:
            return {"accepted": False, "collection": alias, "operation": "sync", "status": "busy"}
        now = time.monotonic()
        if now - self.last_request < 60:
            return {"accepted": False, "collection": alias, "operation": "sync", "status": "rate_limited"}
        if not self.lock.acquire(blocking=False):
            return {"accepted": False, "collection": alias, "operation": "sync", "status": "busy"}
        try:
            before = self._status(alias)
            if self.running_upstream:
                self.lock.release()
                return {"accepted": False, "collection": alias, "operation": "sync", "status": "busy"}
            self.baseline_sync = before.get("last_sync_at")
            self.seen_running = False
            self.active_alias = alias
            self.last_request = now
            self._save_state()
            result = self._request("POST", f"/sync/{alias}")
            if result.get("triggered") is False:
                self.active_alias = None
            if result.get("triggered") is not True or result.get("name") != alias:
                raise RuntimeError("Sync service unavailable")
            self.active_alias = alias
            return {"accepted": True, "collection": alias, "operation": "sync", "status": "accepted"}
        except Exception:
            # A timed-out POST may have reached upstream. Keep ownership until
            # completion is proven, or an operator verifies idle and restarts.
            if self.active_alias is None:
                self.lock.release()
            else:
                self._save_state()
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
    if not os.environ.get("MCP_ALLOWED_HOST", "").strip():
        raise RuntimeError("MCP_ALLOWED_HOST is required")
    state_path = Path(os.environ["BRIDGE_STATE_FILE"])
    owner = acquire_singleton(state_path.parent / "bridge.lock")
    bridge = Bridge(os.environ.get("OIKB_URL", "http://oikb:8080"), read_secret("OIKB_TOKEN_FILE"),
                    state_path=state_path,
                    aliases=parse_aliases(os.environ.get("MCP_APPROVED_ALIASES", ",".join(sorted(ALIASES)))))
    def monitor() -> None:
        while True:
            time.sleep(5)
            try:
                bridge.reconcile()
            except RuntimeError:
                pass
    threading.Thread(target=monitor, daemon=True, name="sync-status").start()
    uvicorn.run(create_app(bridge, read_secret("BRIDGE_TOKEN_FILE")), host="0.0.0.0", port=8000)

if __name__ == "__main__": main()
