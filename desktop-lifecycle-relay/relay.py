#!/usr/bin/env python3
"""Private, fixed-action desktop lifecycle relay."""

import hmac
import json
import os
import re
import socket
import subprocess
import sys
import uuid
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

ACTIONS = frozenset({"wake", "shutdown"})
MAC_RE = re.compile(r"^[0-9A-Fa-f]{2}([:-]?[0-9A-Fa-f]{2}){5}$")
SHUTDOWN_COMMAND = 'shutdown /s /t 0 /d p:4:1 /c "Scheduled weekday shutdown"'


def magic_packet(mac: str) -> bytes:
    if not MAC_RE.fullmatch(mac):
        raise ValueError("invalid MAC address")
    raw = bytes.fromhex(re.sub(r"[:-]", "", mac))
    return b"\xff" * 6 + raw * 16


def _settings(environ: dict[str, str]) -> dict[str, str]:
    required = (
        "RELAY_TOKEN",
        "WOL_MAC",
        "WOL_BROADCAST",
        "WOL_PORT",
        "DESKTOP_SSH_HOST",
        "DESKTOP_SSH_USER",
        "DESKTOP_SSH_KEY",
    )
    missing = [name for name in required if not environ.get(name)]
    if missing:
        raise RuntimeError("relay configuration is incomplete")
    return {name: environ[name] for name in required}


def _wake(settings: dict[str, str]) -> None:
    packet = magic_packet(settings["WOL_MAC"])
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(packet, (settings["WOL_BROADCAST"], int(settings["WOL_PORT"])))
    finally:
        sock.close()


def _shutdown(settings: dict[str, str]) -> None:
    command = [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "ConnectTimeout=10",
        "-o", "StrictHostKeyChecking=yes",
        "-i", settings["DESKTOP_SSH_KEY"],
        f'{settings["DESKTOP_SSH_USER"]}@{settings["DESKTOP_SSH_HOST"]}',
        SHUTDOWN_COMMAND,
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=20, check=False)
    if result.returncode != 0:
        raise RuntimeError("fixed shutdown command was rejected")


ActionHandler = Callable[[str, str, dict[str, str], dict[str, Any] | None], tuple[int, dict[str, str]]]


def make_handler(environ: dict[str, str]) -> ActionHandler:
    settings = _settings(environ)

    def handle(method: str, path: str, headers: dict[str, str], body: dict | None):
        if method == "GET" and path == "/healthz":
            return 200, {"status": "ok"}
        if method != "POST" or path != "/v1/action":
            return 404, {"status": "rejected", "reason": "not_found"}
        expected = "Bearer " + settings["RELAY_TOKEN"]
        supplied = headers.get("Authorization", "")
        if not hmac.compare_digest(supplied, expected):
            return 401, {"status": "rejected", "reason": "unauthorized"}
        action = body.get("action") if isinstance(body, dict) else None
        if action not in ACTIONS:
            return 400, {"status": "rejected", "reason": "invalid_action"}
        request_id = str(uuid.uuid4())
        try:
            if action == "wake":
                _wake(settings)
            else:
                _shutdown(settings)
        except (OSError, RuntimeError, subprocess.TimeoutExpired, ValueError):
            return 502, {"request_id": request_id, "action": action, "status": "failed"}
        return 202, {"request_id": request_id, "action": action, "status": "accepted"}

    return handle


class RequestHandler(BaseHTTPRequestHandler):
    relay_handler: ActionHandler

    def log_message(self, format, *args):
        return

    def _respond(self, status: int, payload: dict) -> None:
        encoded = json.dumps(payload, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self):
        status, payload = self.relay_handler("GET", self.path, dict(self.headers), None)
        self._respond(status, payload)

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length))
        except (ValueError, json.JSONDecodeError):
            self._respond(400, {"status": "rejected", "reason": "invalid_json"})
            return
        status, payload = self.relay_handler("POST", self.path, dict(self.headers), body)
        self._respond(status, payload)


def main() -> None:
    host = os.environ.get("RELAY_BIND_HOST", "127.0.0.1")
    port = int(os.environ.get("RELAY_PORT", "8790"))
    RequestHandler.relay_handler = make_handler(dict(os.environ))
    ThreadingHTTPServer((host, port), RequestHandler).serve_forever()


if __name__ == "__main__":
    main()
