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
    def test_destination_rejects_ssh_option_injection(self):
        for host in ("-oProxyCommand=bad", "ally;reboot", "ally name"):
            with self.subTest(host=host), self.assertRaises(ValueError):
                remote_capture.validate_destination(host, "deck", 22)

    def test_ssh_command_and_payload_are_fixed_and_shell_free(self):
        safe_capture = {
            "schema_version": 1,
            "collector": {"read_only": True},
            "diagnostics": {"snapshot": {"support_tier": "certified"}},
            "errors": [],
        }

        class Result:
            returncode = 0
            stdout = json.dumps(safe_capture)

        with patch("remote_capture.subprocess.run", return_value=Result()) as run:
            value = remote_capture.collect_remote(host="192.168.1.172")
        argv = run.call_args.args[0]
        self.assertEqual(argv[-3:], ["deck@192.168.1.172", "python3", "-"])
        self.assertNotIn("shell", run.call_args.kwargs)
        self.assertEqual(
            run.call_args.kwargs["input"],
            remote_capture.PAYLOAD.read_text(encoding="utf-8"),
        )
        self.assertEqual(len(value["collector"]["payload_sha256"]), 64)

    def test_parser_rejects_private_process_fields(self):
        value = {
            "schema_version": 1,
            "collector": {"read_only": True},
            "process": {"pid": 123},
        }
        with self.assertRaisesRegex(ValueError, "forbidden field"):
            remote_capture.parse_capture(json.dumps(value), "a" * 64)

    def test_save_is_exclusive_and_bounded(self):
        value = {
            "schema_version": 1,
            "collector": {"read_only": True, "payload_sha256": "a" * 64},
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


if __name__ == "__main__":
    unittest.main()
