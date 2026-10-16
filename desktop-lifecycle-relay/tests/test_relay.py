import io
import json
import os
import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))
import relay


class FakeSocket:
    def __init__(self):
        self.options = []
        self.sent = []

    def setsockopt(self, *args):
        self.options.append(args)

    def sendto(self, packet, target):
        self.sent.append((packet, target))

    def close(self):
        pass


class RelayTests(unittest.TestCase):
    def setUp(self):
        self.env = {
            "RELAY_TOKEN": "test-token",
            "WOL_MAC": "00:11:22:33:44:55",
            "WOL_BROADCAST": "192.0.2.255",
            "WOL_PORT": "9",
            "DESKTOP_SSH_HOST": "desktop.example.internal",
            "DESKTOP_SSH_USER": "automation",
            "DESKTOP_SSH_KEY": "/run/desktop_lifecycle/key",
        }

    def test_magic_packet_is_6_ff_then_16_mac_repeats(self):
        packet = relay.magic_packet("00:11:22:33:44:55")
        self.assertEqual(packet, b"\xff" * 6 + bytes.fromhex("001122334455") * 16)

    def test_magic_packet_rejects_bad_mac(self):
        with self.assertRaises(ValueError):
            relay.magic_packet("bad-mac")

    def test_unauthenticated_action_is_rejected(self):
        app = relay.make_handler(self.env)
        status, payload = app("POST", "/v1/action", {}, {"action": "wake"})
        self.assertEqual(status, 401)
        self.assertEqual(payload["status"], "rejected")

    def test_invalid_action_is_rejected(self):
        app = relay.make_handler(self.env)
        status, payload = app(
            "POST", "/v1/action", {"Authorization": "Bearer test-token"}, {"action": "anything"}
        )
        self.assertEqual(status, 400)
        self.assertEqual(payload["status"], "rejected")

    def test_wake_only_sends_magic_packet(self):
        app = relay.make_handler(self.env)
        fake = FakeSocket()
        with patch("relay.socket.socket", return_value=fake), patch("relay.uuid.uuid4", return_value="request-1"):
            status, payload = app(
                "POST", "/v1/action", {"Authorization": "Bearer test-token"}, {"action": "wake"}
            )
        self.assertEqual(status, 202)
        self.assertEqual(payload, {"request_id": "request-1", "action": "wake", "status": "accepted"})
        self.assertEqual(len(fake.sent), 1)
        self.assertEqual(fake.sent[0][1], ("192.0.2.255", 9))

    def test_shutdown_executes_only_fixed_command(self):
        app = relay.make_handler(self.env)
        recorded = []
        def fake_run(command, **kwargs):
            recorded.append(command)
            return type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})()
        with patch("relay.subprocess.run", fake_run), patch("relay.uuid.uuid4", return_value="request-2"):
            status, payload = app(
                "POST", "/v1/action", {"Authorization": "Bearer test-token"}, {"action": "shutdown"}
            )
        self.assertEqual(status, 202)
        self.assertEqual(payload, {"request_id": "request-2", "action": "shutdown", "status": "accepted"})
        self.assertEqual(len(recorded), 1)
        self.assertEqual(recorded[0][-1], "shutdown /s /t 0 /d p:4:1 /c \"Scheduled weekday shutdown\"")
        self.assertNotIn("anything", " ".join(recorded[0]))

    def test_health_has_no_secrets(self):
        app = relay.make_handler(self.env)
        status, payload = app("GET", "/healthz", {}, None)
        self.assertEqual(status, 200)
        self.assertEqual(payload, {"status": "ok"})
        self.assertNotIn("test-token", json.dumps(payload))


if __name__ == "__main__":
    unittest.main()
