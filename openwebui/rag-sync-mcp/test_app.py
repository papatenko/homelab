import asyncio
import unittest
from unittest.mock import Mock
import httpx
from app import ALIASES, Bridge, create_app

class BridgeTests(unittest.TestCase):
    def test_fixed_alias_tool_surface(self):
        app = create_app(Bridge("http://oikb:8080", "secret", Mock()), "bridge")
        names = {getattr(route, "path", None) for route in app.routes}
        self.assertIn("/mcp", names)
        self.assertEqual(ALIASES, {"cosc-4337", "cosc-4351", "cosc-4397", "mark-3336"})
    def test_unknown_alias_and_extra_args_make_no_call(self):
        client = Mock(); bridge = Bridge("http://oikb:8080", "secret", client)
        for args in ({"collection": "bogus"}, {"collection": "cosc-4337", "url": "http://evil"}):
            with self.assertRaises(ValueError): bridge.invoke("sync_knowledge_base", args)
        client.request.assert_not_called()
    def test_sync_and_status_lock_until_terminal(self):
        client = Mock(); client.request.return_value.json.side_effect = [
            {"sources": {"source": {"name": "cosc-4337", "status": "success", "last_sync": 1}}},
            {"triggered": True, "name": "cosc-4337"},
            {"sources": {"source": {"name": "cosc-4337", "status": "success", "last_sync": 1}}},
            {"sources": {"source": {"name": "cosc-4337", "status": "running"}}},
            {"sources": {"source": {"name": "cosc-4337", "status": "success", "last_sync": 2}}},
        ]
        bridge = Bridge("http://oikb:8080", "secret", client)
        result = bridge.invoke("sync_knowledge_base", {"collection": "cosc-4337"})
        self.assertEqual(result["status"], "accepted")
        self.assertFalse(bridge.invoke("sync_knowledge_base", {"collection": "cosc-4351"})["accepted"])
        self.assertEqual(bridge.invoke("get_sync_status", {"collection": "cosc-4337"})["state"], "unknown")
        self.assertTrue(bridge.lock.locked())
        self.assertEqual(bridge.invoke("get_sync_status", {"collection": "cosc-4337"})["state"], "running")
        self.assertTrue(bridge.lock.locked())
        status = bridge.invoke("get_sync_status", {"collection": "cosc-4337"})
        self.assertEqual(status["state"], "success")
        self.assertFalse(bridge.lock.locked())
        self.assertNotIn("secret", str(status))
    def test_upstream_http_errors_are_not_accepted(self):
        client = Mock(); client.request.return_value.raise_for_status.side_effect = [None, httpx.HTTPStatusError("bad", request=Mock(), response=Mock())]
        client.request.return_value.json.return_value = {"sources": {}}
        bridge = Bridge("http://oikb:8080", "secret", client)
        with self.assertRaises(RuntimeError): bridge.invoke("sync_knowledge_base", {"collection": "cosc-4337"})
        self.assertFalse(bridge.lock.locked())
    def test_auth_http_enforced(self):
        async def run():
            app = create_app(Bridge("http://oikb:8080", "x", Mock()), "token")
            transport = httpx.ASGITransport(app=app)
            async with app.router.lifespan_context(app):
                async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as client:
                    denied = await client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
                    allowed = await client.post("/mcp", headers={"Authorization": "Bearer token", "Accept": "application/json, text/event-stream"}, json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
                    return denied, allowed
        denied, allowed = asyncio.run(run())
        self.assertEqual(denied.status_code, 401)
        self.assertEqual(allowed.status_code, 200)

    def test_protocol_initialize_and_tool_validation(self):
        async def run():
            client_upstream = Mock()
            app = create_app(Bridge("http://oikb:8080", "secret", client_upstream), "token")
            async with app.router.lifespan_context(app):
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost") as client:
                    headers = {"Authorization": "Bearer token", "Accept": "application/json, text/event-stream"}
                    init = await client.post("/mcp", headers=headers, json={"jsonrpc":"2.0", "id":1, "method":"initialize", "params":{"protocolVersion":"2025-03-26", "capabilities":{}, "clientInfo":{"name":"test", "version":"1"}}})
                    listing = await client.post("/mcp", headers=headers, json={"jsonrpc":"2.0", "id":2, "method":"tools/list"})
                    malformed = await client.post("/mcp", headers=headers, json={"jsonrpc":"2.0", "id":3, "method":"tools/call", "params":{"name":"sync_knowledge_base", "arguments":{"collection":"bad"}}})
                    extra = await client.post("/mcp", headers=headers, json={"jsonrpc":"2.0", "id":4, "method":"tools/call", "params":{"name":"sync_knowledge_base", "arguments":{"collection":"cosc-4337", "url":"bad"}}})
                    return init, listing, malformed, extra, client_upstream
        init, listing, malformed, extra, upstream = asyncio.run(run())
        self.assertEqual(init.status_code, 200)
        self.assertEqual({x["name"] for x in listing.json()["result"]["tools"]}, {"sync_knowledge_base", "get_sync_status"})
        self.assertTrue(malformed.json()["result"]["isError"])
        self.assertTrue(extra.json()["result"]["isError"])
        upstream.request.assert_not_called()
    def test_upstream_rejected_trigger_does_not_claim_acceptance(self):
        client = Mock(); client.request.return_value.json.side_effect = [{"sources": {}}, {"triggered": False, "error": "private"}]
        bridge = Bridge("http://oikb:8080", "secret", client)
        with self.assertRaisesRegex(RuntimeError, "Sync service unavailable"):
            bridge.invoke("sync_knowledge_base", {"collection":"cosc-4337"})
        self.assertFalse(bridge.lock.locked())

if __name__ == "__main__": unittest.main()
