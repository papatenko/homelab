import asyncio
import unittest
from unittest.mock import Mock
import httpx
from app import ALIASES, Bridge, create_app

class BridgeTests(unittest.TestCase):
    def test_invalid_alias_configuration_is_rejected(self):
        for aliases in (set(), {"../sync/all"}, {"bad alias"}, {"x" * 81}):
            with self.assertRaises(ValueError):
                Bridge("http://oikb:8080", "secret", Mock(), aliases=aliases)

    def test_explicit_allowlist_is_extensible_but_never_auto_discovers(self):
        client = Mock()
        client.request.return_value.json.side_effect = [
            {"sources": {"future-kb": {"status": "idle"}}},
            {"triggered": True, "name": "future-kb"},
        ]
        approved = Bridge("http://oikb:8080", "secret", client, aliases={"future-kb"})
        self.assertTrue(approved.invoke("sync_knowledge_base", {"collection": "future-kb"})["accepted"])
        denied = Bridge("http://oikb:8080", "secret", Mock(), aliases={"cosc-4337"})
        with self.assertRaises(ValueError):
            denied.invoke("sync_knowledge_base", {"collection": "future-kb"})
        denied.client.request.assert_not_called()

    def test_single_process_guard_rejects_second_owner(self):
        import tempfile
        from pathlib import Path
        from app import acquire_singleton
        with tempfile.TemporaryDirectory() as directory:
            first = acquire_singleton(Path(directory) / "bridge.lock")
            try:
                with self.assertRaisesRegex(RuntimeError, "already running"):
                    acquire_singleton(Path(directory) / "bridge.lock")
            finally:
                first.close()
            again = acquire_singleton(Path(directory) / "bridge.lock")
            again.close()

    def test_incomplete_other_source_health_blocks_dispatch(self):
        client = Mock()
        client.request.return_value.json.return_value = {"sources": {
            "cosc-4337": {"status": "idle"}, "cosc-4351": {"status": "mystery"}}}
        bridge = Bridge("http://oikb:8080", "secret", client)
        with self.assertRaisesRegex(RuntimeError, "Sync service unavailable"):
            bridge.invoke("sync_knowledge_base", {"collection": "cosc-4337"})
        self.assertTrue(all(c.args[0] == "GET" for c in client.request.call_args_list))

    def test_corrupt_state_preserves_status_but_blocks_new_sync(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as state_dir:
            state = Path(state_dir) / "pending.json"
            state.write_text("not-json")
            client = Mock()
            client.request.return_value.json.return_value = {"sources": {"cosc-4337": {"status": "idle"}}}
            bridge = Bridge("http://oikb:8080", "secret", client, state_path=state)
            self.assertEqual(bridge.invoke("sync_knowledge_base", {"collection": "cosc-4337"})["status"], "busy")
            self.assertEqual(bridge.invoke("get_sync_status", {"collection": "cosc-4337"})["state"], "idle")
            self.assertFalse(any(c.args[0] == "POST" for c in client.request.call_args_list))

    def test_invalid_persisted_state_blocks_dispatch(self):
        import json
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as state_dir:
            state = Path(state_dir) / "pending.json"
            for payload in ({}, {"active_alias": "bogus", "baseline_sync": 1, "seen_running": False},
                            {"active_alias": None}):
                state.write_text(json.dumps(payload))
                client = Mock()
                bridge = Bridge("http://oikb:8080", "secret", client, state_path=state)
                self.assertEqual(bridge.invoke("sync_knowledge_base", {"collection": "cosc-4337"})["status"], "busy")
                client.request.assert_not_called()

    def test_pending_job_survives_restart_and_blocks_dispatch_until_fresh_completion(self):
        import tempfile
        with tempfile.TemporaryDirectory() as state_dir:
            client = Mock()
            client.request.side_effect = [
                Mock(json=lambda: {"sources": {"cosc-4337": {"status": "idle", "last_sync": 1}}}, raise_for_status=Mock()),
                Mock(json=lambda: {"triggered": True, "name": "cosc-4337"}, raise_for_status=Mock()),
            ]
            first = Bridge("http://oikb:8080", "secret", client, state_path=f"{state_dir}/pending.json")
            first.invoke("sync_knowledge_base", {"collection": "cosc-4337"})

            restarted_client = Mock()
            restarted_client.request.return_value.json.return_value = {"sources": {
                "cosc-4337": {"status": "idle", "last_sync": 1}}}
            restarted = Bridge("http://oikb:8080", "secret", restarted_client,
                               state_path=f"{state_dir}/pending.json")
            self.assertEqual(restarted.invoke("sync_knowledge_base", {"collection": "cosc-4337"})["status"], "busy")
            self.assertEqual([c.args[0] for c in restarted_client.request.call_args_list], [])
            restarted_client.request.return_value.json.return_value = {"sources": {
                "cosc-4337": {"status": "running", "last_sync": 1}}}
            self.assertEqual(restarted.invoke("get_sync_status", {"collection": "cosc-4337"})["state"], "running")
            restarted_client.request.return_value.json.return_value = {"sources": {
                "cosc-4337": {"status": "success", "last_sync": 2}}}
            self.assertEqual(restarted.invoke("get_sync_status", {"collection": "cosc-4337"})["state"], "success")
            self.assertEqual(restarted.active_alias, None)

    def test_unknown_health_state_fails_closed_without_post(self):
        client = Mock()
        client.request.return_value.json.return_value = {"sources": {}}
        bridge = Bridge("http://oikb:8080", "secret", client)
        with self.assertRaisesRegex(RuntimeError, "Sync service unavailable"):
            bridge.invoke("sync_knowledge_base", {"collection": "cosc-4337"})
        self.assertTrue(all(call.args[0] == "GET" for call in client.request.call_args_list))
        self.assertFalse(bridge.lock.locked())

    def test_external_running_source_blocks_new_sync(self):
        client = Mock()
        client.request.return_value.json.return_value = {"sources": {
            alias: {"name": alias, "status": "running" if alias == "mark-3336" else "idle"}
            for alias in ALIASES}}
        bridge = Bridge("http://oikb:8080", "secret", client)
        result = bridge.invoke("sync_knowledge_base", {"collection": "cosc-4337"})
        self.assertEqual(result["status"], "busy")
        self.assertTrue(all(call.args[0] == "GET" for call in client.request.call_args_list))

    def test_reconcile_releases_completed_job_without_client_poll(self):
        client = Mock()
        client.request.return_value.json.return_value = {"sources": {
            "cosc-4337": {"status": "success", "last_sync": 2}}}
        bridge = Bridge("http://oikb:8080", "secret", client)
        bridge.lock.acquire()
        bridge.active_alias, bridge.baseline_sync = "cosc-4337", 1
        bridge.reconcile()
        self.assertIsNone(bridge.active_alias)
        self.assertFalse(bridge.lock.locked())

    def test_ambiguous_trigger_timeout_keeps_lock(self):
        client = Mock()
        def request(method, *args, **kwargs):
            if method == "POST": raise httpx.ReadTimeout("private")
            response = Mock()
            response.json.return_value = {"sources": {alias: {"status": "idle"} for alias in ALIASES}}
            return response
        client.request.side_effect = request
        bridge = Bridge("http://oikb:8080", "secret", client)
        with self.assertRaises(RuntimeError):
            bridge.invoke("sync_knowledge_base", {"collection": "cosc-4337"})
        self.assertTrue(bridge.lock.locked())
        self.assertEqual(bridge.active_alias, "cosc-4337")

    def test_sync_requests_are_throttled(self):
        client = Mock()
        client.request.return_value.json.side_effect = [
            {"sources": {alias: {"status": "idle"} for alias in ALIASES}},
            {"triggered": True, "name": "cosc-4337"},
        ]
        bridge = Bridge("http://oikb:8080", "secret", client)
        self.assertTrue(bridge.invoke("sync_knowledge_base", {"collection": "cosc-4337"})["accepted"])
        bridge.active_alias = None
        bridge.lock.release()
        self.assertEqual(bridge.invoke("sync_knowledge_base", {"collection": "cosc-4337"})["status"], "rate_limited")

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
        client = Mock()
        client.request.return_value.raise_for_status.side_effect = [None, httpx.HTTPStatusError("bad", request=Mock(), response=Mock())]
        client.request.return_value.json.return_value = {"sources": {alias: {"status": "idle"} for alias in ALIASES}}
        bridge = Bridge("http://oikb:8080", "secret", client)
        with self.assertRaises(RuntimeError): bridge.invoke("sync_knowledge_base", {"collection": "cosc-4337"})
        # An HTTP failure after dispatch does not prove the job was not started.
        self.assertTrue(bridge.lock.locked())
        self.assertEqual(bridge.active_alias, "cosc-4337")
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
