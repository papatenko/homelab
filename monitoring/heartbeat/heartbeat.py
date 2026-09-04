#!/usr/bin/env python3
"""Run a trusted local job and emit a dead-man heartbeat after verification.

All endpoints and credentials are runtime inputs. This module deliberately never
captures or prints child-process output, URLs, or credential values.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class HeartbeatConfig:
    command: str
    verify: str
    timeout: float = 900.0
    healthcheck_success_url: Optional[str] = None
    healthcheck_failure_url: Optional[str] = None
    ntfy_url: Optional[str] = None
    ntfy_topic: Optional[str] = None
    ntfy_token: Optional[str] = None

    @classmethod
    def from_env(cls) -> "HeartbeatConfig":
        command = os.environ.get("HEARTBEAT_COMMAND", "").strip()
        verify = os.environ.get("HEARTBEAT_VERIFY", "").strip()
        if not command or not verify:
            raise ValueError("HEARTBEAT_COMMAND and HEARTBEAT_VERIFY are required")
        try:
            timeout = float(os.environ.get("HEARTBEAT_TIMEOUT", "900"))
        except ValueError as exc:
            raise ValueError("HEARTBEAT_TIMEOUT must be numeric") from exc
        if timeout <= 0:
            raise ValueError("HEARTBEAT_TIMEOUT must be positive")
        return cls(
            command=command,
            verify=verify,
            timeout=timeout,
            healthcheck_success_url=os.environ.get("HEALTHCHECKS_SUCCESS_URL") or None,
            healthcheck_failure_url=os.environ.get("HEALTHCHECKS_FAILURE_URL") or None,
            ntfy_url=os.environ.get("NTFY_URL") or None,
            ntfy_topic=os.environ.get("NTFY_TOPIC") or None,
            ntfy_token=os.environ.get("NTFY_TOKEN") or None,
        )


@dataclass(frozen=True)
class RunResult:
    success: bool
    reason: str


class NotificationPublisher:
    """Value-free HTTP publisher for Healthchecks and optional ntfy."""

    def __init__(self, config: HeartbeatConfig):
        self.config = config

    def _post(self, url: str, data: bytes = b"", headers: Optional[dict[str, str]] = None) -> None:
        request = urllib.request.Request(url, data=data, method="POST", headers=headers or {})
        # Do not include the URL or exception text in any raised/logged message.
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                if response.status >= 400:
                    raise RuntimeError("notification endpoint rejected request")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise RuntimeError("notification endpoint unavailable") from exc

    def healthcheck(self, status: str) -> None:
        url = self.config.healthcheck_success_url if status == "success" else self.config.healthcheck_failure_url
        if url:
            self._post(url)

    def ntfy(self, title: str, message: str) -> None:
        if not self.config.ntfy_url or not self.config.ntfy_topic:
            return
        url = self.config.ntfy_url.rstrip("/") + "/" + self.config.ntfy_topic.lstrip("/")
        headers = {"Title": title, "Content-Type": "text/plain; charset=utf-8"}
        if self.config.ntfy_token:
            headers["Authorization"] = "Bearer " + self.config.ntfy_token
        self._post(url, message.encode("utf-8"), headers)


class HeartbeatRunner:
    def __init__(self, config: HeartbeatConfig, publisher: NotificationPublisher):
        self.config = config
        self.publisher = publisher

    def _command(self, command: str) -> tuple[str, Optional[int]]:
        try:
            completed = subprocess.run(
                command,
                shell=True,
                executable="/bin/sh",
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=self.config.timeout,
                check=False,
            )
            return "ok" if completed.returncode == 0 else "command", completed.returncode
        except subprocess.TimeoutExpired:
            return "timeout", None
        except OSError:
            return "command", None

    def _notify(self, status: str, title: str, message: str) -> bool:
        try:
            self.publisher.healthcheck(status)
            self.publisher.ntfy(title, message)
            return True
        except Exception:
            return False

    def run(self) -> RunResult:
        command_reason, _ = self._command(self.config.command)
        if command_reason != "ok":
            self._notify("failure", "Heartbeat failure", "Job failed or timed out before verification.")
            return RunResult(False, command_reason)

        verify_reason, _ = self._command(self.config.verify)
        if verify_reason != "ok":
            self._notify("failure", "Heartbeat failure", "Post-verification failed; success was not emitted.")
            return RunResult(False, verify_reason)

        if not self._notify("success", "Heartbeat success", "Job and post-verification completed successfully."):
            return RunResult(False, "notification")
        return RunResult(True, "success")


def main() -> int:
    try:
        config = HeartbeatConfig.from_env()
    except ValueError as exc:
        # Fixed, sanitized error text; never print environment values.
        print(f"heartbeat configuration error: {exc}", file=sys.stderr)
        return 64
    result = HeartbeatRunner(config, NotificationPublisher(config)).run()
    print(f"heartbeat {result.reason}")
    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
