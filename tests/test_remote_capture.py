from __future__ import annotations

import ast
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import remote_capture  # noqa: E402


class RemoteCaptureTests(unittest.TestCase):
    @staticmethod
    def _collector():
        return {
            "read_only": True,
            "remote_files_written": False,
            "transport": "ssh_stdin",
            "execution_privilege": "unprivileged",
        }

    @staticmethod
    def _wake_diagnostics():
        return {
            "applicable": True,
            "bridge_wakeup": "enabled",
            "function_wakeup": {"enabled": 2, "disabled": 1, "unknown": 0},
            "function_runtime": {"active": 2, "suspended": 1, "unknown": 0},
            "reason": "wake.read_only_capability_observed",
        }

    def test_destination_rejects_ssh_option_injection(self):
        for host in ("-oProxyCommand=bad", "ally;reboot", "ally name"):
            with self.subTest(host=host), self.assertRaises(ValueError):
                remote_capture.validate_destination(host, "deck", 22)

    def test_ssh_command_and_payload_are_fixed_and_shell_free(self):
        safe_capture = {
            "schema_version": 1,
            "collector": {
                "read_only": True,
                "remote_files_written": False,
                "transport": "ssh_stdin",
                "execution_privilege": "unprivileged",
            },
            "diagnostics": {"snapshot": {"support_tier": "certified"}},
            "errors": [],
        }

        class Result:
            returncode = 0
            stdout = json.dumps(safe_capture)

        with patch("remote_capture.subprocess.run", return_value=Result()) as run:
            value = remote_capture.collect_remote(host="192.0.2.172")
        argv = run.call_args.args[0]
        self.assertEqual(argv[-3:], ["deck@192.0.2.172", "python3", "-"])
        self.assertNotIn("shell", run.call_args.kwargs)
        self.assertEqual(
            run.call_args.kwargs["input"],
            remote_capture.PAYLOAD.read_text(encoding="utf-8"),
        )
        self.assertEqual(len(value["collector"]["payload_sha256"]), 64)

    def test_root_read_only_command_is_fixed_and_privilege_is_verified(self):
        safe_capture = {
            "schema_version": 1,
            "collector": {
                "read_only": True,
                "remote_files_written": False,
                "transport": "ssh_stdin",
                "execution_privilege": "root_read_only",
            },
            "diagnostics": None,
            "errors": [],
        }

        class Result:
            returncode = 0
            stdout = json.dumps(safe_capture)

        with patch("remote_capture.subprocess.run", return_value=Result()) as run:
            remote_capture.collect_remote(
                host="192.0.2.172",
                root_read_only=True,
            )
        self.assertEqual(
            run.call_args.args[0][-5:],
            ["deck@192.0.2.172", "sudo", "-n", "/usr/bin/python3", "-"],
        )
        self.assertNotIn("shell", run.call_args.kwargs)

    def test_root_read_only_rejects_unprivileged_result(self):
        value = {
            "schema_version": 1,
            "collector": {
                "read_only": True,
                "remote_files_written": False,
                "transport": "ssh_stdin",
                "execution_privilege": "unprivileged",
            },
        }
        with self.assertRaisesRegex(ValueError, "requested privilege"):
            remote_capture.parse_capture(
                json.dumps(value),
                "a" * 64,
                expected_privilege="root_read_only",
            )

    def test_root_read_only_failure_does_not_retry_or_expose_remote_stderr(self):
        class Result:
            returncode = 1
            stdout = ""
            stderr = "private remote diagnostic"

        with patch("remote_capture.subprocess.run", return_value=Result()) as run:
            with self.assertRaisesRegex(
                RuntimeError,
                r"non-interactive root read-only capture unavailable \(SSH status 1\)",
            ) as raised:
                remote_capture.collect_remote(
                    host="192.0.2.172",
                    root_read_only=True,
                )
        self.assertEqual(run.call_count, 1)
        self.assertNotIn("private remote diagnostic", str(raised.exception))

    def test_unprivileged_failure_is_categorical_without_remote_stderr(self):
        class Result:
            returncode = 255
            stdout = ""
            stderr = "deck@192.0.2.141: Permission denied (publickey,password)."

        with patch("remote_capture.subprocess.run", return_value=Result()):
            with self.assertRaisesRegex(
                RuntimeError, r"ssh\.authentication_failed"
            ) as raised:
                remote_capture.collect_remote(host="192.0.2.141")
        self.assertNotIn("192.0.2.141", str(raised.exception))
        self.assertNotIn("publickey", str(raised.exception))

    def test_ssh_failure_classification_is_fixed_and_non_sensitive(self):
        cases = {
            "Permission denied (publickey).": "ssh.authentication_failed",
            "Host key verification failed.": "ssh.host_key_unverified",
            "Could not resolve hostname ally: Name or service not known": "ssh.host_unresolved",
            "connect to host ally port 22: Connection refused": "ssh.connection_refused",
            "connect to host ally port 22: No route to host": "ssh.network_unreachable",
            "Connection timed out": "ssh.connection_timed_out",
            "private diagnostic token=secret": "ssh.connection_failed",
        }
        for stderr, expected in cases.items():
            with self.subTest(expected=expected):
                self.assertEqual(remote_capture.ssh_failure_code(255, stderr), expected)
        self.assertEqual(
            remote_capture.ssh_failure_code(1, "private remote failure"),
            "ssh.remote_command_failed",
        )

    def test_parser_rejects_private_process_fields(self):
        value = {
            "schema_version": 1,
            "collector": {
                "read_only": True,
                "remote_files_written": False,
                "transport": "ssh_stdin",
                "execution_privilege": "unprivileged",
            },
            "process": {"pid": 123},
        }
        with self.assertRaisesRegex(ValueError, "forbidden field"):
            remote_capture.parse_capture(json.dumps(value), "a" * 64)

    def test_parser_accepts_only_the_documented_wake_diagnostics_schema(self):
        value = {
            "schema_version": 1,
            "collector": self._collector(),
            "wake_diagnostics": self._wake_diagnostics(),
        }

        parsed = remote_capture.parse_capture(json.dumps(value), "a" * 64)
        self.assertEqual(parsed["wake_diagnostics"]["bridge_wakeup"], "enabled")

    def test_parser_rejects_malformed_wake_diagnostics_before_use_as_evidence(self):
        for changes in (
            {"bridge_wakeup": "maybe"},
            {"reason": "wake source 0000:01:00.0"},
            {"function_wakeup": {"enabled": 65, "disabled": 0, "unknown": 0}},
            {"unexpected": "field"},
        ):
            with self.subTest(changes=changes):
                wake = self._wake_diagnostics()
                wake.update(changes)
                value = {
                    "schema_version": 1,
                    "collector": self._collector(),
                    "wake_diagnostics": wake,
                }
                with self.assertRaisesRegex(ValueError, "wake diagnostics"):
                    remote_capture.parse_capture(json.dumps(value), "a" * 64)

    def test_save_is_exclusive_and_bounded(self):
        value = {
            "schema_version": 1,
            "collector": {
                "read_only": True,
                "remote_files_written": False,
                "transport": "ssh_stdin",
                "execution_privilege": "unprivileged",
                "payload_sha256": "a" * 64,
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "capture.json"
            remote_capture.save_capture(value, output)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), value)
            with self.assertRaises(FileExistsError):
                remote_capture.save_capture(value, output)

    def test_remote_payload_has_no_process_or_filesystem_mutation_imports(self):
        path = ROOT / "scripts" / "remote_capture_payload.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported = {
            alias.name.split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imported.update(
            node.module.split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        )
        self.assertTrue({"subprocess", "socket", "urllib", "http"}.isdisjoint(imported))
        forbidden_calls = {
            "chmod",
            "mkdir",
            "rename",
            "replace",
            "rmdir",
            "symlink_to",
            "touch",
            "unlink",
            "write_bytes",
            "write_text",
        }
        called = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        self.assertTrue(forbidden_calls.isdisjoint(called))
        self.assertEqual(len(hashlib.sha256(source.encode("utf-8")).hexdigest()), 64)

    def test_payload_marks_plugin_lifecycle_guard_as_not_observed(self):
        source = (ROOT / "scripts" / "remote_capture_payload.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("plugin_lifecycle_sleep_guard_not_observed", source)
        self.assertIn('row["result"] = "not_observed"', source)

    def test_payload_hashes_the_installed_package_manifest_for_version_provenance(self):
        source = (ROOT / "scripts" / "remote_capture_payload.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('Path("package.json")', source)
        self.assertIn('Path("plugin.json")', source)

    def test_payload_reads_only_the_static_archive_build_label(self):
        source = (ROOT / "scripts" / "remote_capture_payload.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('BUILD_INFO_FILENAME = "build_info.json"', source)
        self.assertIn('"build": _build_info()', source)
        self.assertNotIn("subprocess", source)
        self.assertNotIn(".git", source)

    def test_payload_reports_privilege_without_identity(self):
        source = (ROOT / "scripts" / "remote_capture_payload.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('"root_read_only" if is_root else "unprivileged"', source)
        self.assertNotIn("getlogin", source)


if __name__ == "__main__":
    unittest.main()
