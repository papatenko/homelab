import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1]))

from heartbeat import HeartbeatConfig, HeartbeatRunner  # noqa: E402


class RecordingPublisher:
    def __init__(self):
        self.events = []

    def healthcheck(self, url):
        self.events.append(("healthcheck", url))

    def ntfy(self, title, message):
        self.events.append(("ntfy", title, message))


class HeartbeatRunnerTests(unittest.TestCase):
    def config(self, **overrides):
        values = dict(command="true", verify="true", timeout=3)
        values.update(overrides)
        return HeartbeatConfig(**values)

    def test_success_is_published_only_after_command_and_verification(self):
        publisher = RecordingPublisher()
        runner = HeartbeatRunner(self.config(), publisher)

        result = runner.run()

        self.assertTrue(result.success)
        self.assertEqual(["healthcheck", "ntfy"], [event[0] for event in publisher.events])
        self.assertEqual("success", publisher.events[0][1])

    def test_verification_is_not_run_or_success_published_after_command_failure(self):
        publisher = RecordingPublisher()
        runner = HeartbeatRunner(self.config(command="false", verify="touch SHOULD_NOT_EXIST"), publisher)

        result = runner.run()

        self.assertFalse(result.success)
        self.assertEqual(["healthcheck", "ntfy"], [event[0] for event in publisher.events])
        self.assertEqual("failure", publisher.events[0][1])
        self.assertFalse(Path("SHOULD_NOT_EXIST").exists())

    def test_verification_failure_sends_failure_and_no_success(self):
        publisher = RecordingPublisher()
        runner = HeartbeatRunner(self.config(command="true", verify="false"), publisher)

        result = runner.run()

        self.assertFalse(result.success)
        self.assertEqual("failure", publisher.events[0][1])
        self.assertNotIn("success", [event[1] for event in publisher.events if event[0] == "healthcheck"])

    def test_timeout_terminates_descendants_in_the_job_process_group(self):
        publisher = RecordingPublisher()
        with tempfile.TemporaryDirectory() as directory:
            pid_file = Path(directory) / "child.pid"
            command = (
                f'{sys.executable} -c "import os,time; '
                f'open({str(pid_file)!r}, \'w\').write(str(os.getpid())); '
                'time.sleep(30)" & wait'
            )
            runner = HeartbeatRunner(self.config(command=command, timeout=0.1), publisher)

            result = runner.run()

            self.assertTrue(pid_file.exists(), "test child did not start")
            child_pid = int(pid_file.read_text())
            self.assertFalse(result.success)
            self.assertEqual("timeout", result.reason)
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                try:
                    os.kill(child_pid, 0)
                except ProcessLookupError:
                    break
                time.sleep(0.01)
            else:
                self.fail(f"timed-out child process {child_pid} is still running")

    def test_timeout_is_explicit_failure_without_leaking_output(self):
        publisher = RecordingPublisher()
        command = f'{sys.executable} -c "import time; print(\'SECRET_VALUE\'); time.sleep(2)"'
        runner = HeartbeatRunner(self.config(command=command, timeout=0.05), publisher)

        result = runner.run()

        self.assertFalse(result.success)
        self.assertEqual("timeout", result.reason)
        self.assertNotIn("SECRET_VALUE", str(publisher.events))

    def test_success_notification_failure_is_not_reported_as_success(self):
        publisher = RecordingPublisher()
        publisher.healthcheck = lambda url: (_ for _ in ()).throw(RuntimeError("network"))
        runner = HeartbeatRunner(self.config(), publisher)

        result = runner.run()

        self.assertFalse(result.success)
        self.assertEqual("notification", result.reason)

    def test_producer_identity_is_in_sanitized_ntfy_event(self):
        publisher = RecordingPublisher()
        runner = HeartbeatRunner(self.config(producer="nas-rsync"), publisher)

        result = runner.run()

        self.assertTrue(result.success)
        ntfy_event = next(event for event in publisher.events if event[0] == "ntfy")
        self.assertIn("nas-rsync", ntfy_event[1])
        self.assertIn("producer=nas-rsync", ntfy_event[2])

    def test_environment_configuration_does_not_require_endpoints(self):
        with patch.dict(os.environ, {"HEARTBEAT_COMMAND": "true", "HEARTBEAT_VERIFY": "true"}, clear=True):
            config = HeartbeatConfig.from_env()
        self.assertIsNone(config.healthcheck_success_url)
        self.assertIsNone(config.ntfy_url)

    def test_environment_configuration_rejects_unsafe_producer_identity(self):
        with patch.dict(
            os.environ,
            {
                "HEARTBEAT_COMMAND": "true",
                "HEARTBEAT_VERIFY": "true",
                "HEARTBEAT_PRODUCER": "../secret",
            },
            clear=True,
        ):
            with self.assertRaisesRegex(ValueError, "safe identifier"):
                HeartbeatConfig.from_env()


if __name__ == "__main__":
    unittest.main()
