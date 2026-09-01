from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import compare_wake_captures  # noqa: E402


def capture(*, wake_diagnostics):
    return {
        "schema_version": 1,
        "collector": {
            "read_only": True,
            "remote_files_written": False,
            "transport": "ssh_stdin",
            "execution_privilege": "root_read_only",
            "payload_sha256": "a" * 64,
        },
        "wake_diagnostics": wake_diagnostics,
        "errors": [],
    }


def wake(*, bridge="enabled", enabled=2, disabled=1, unknown=0, active=2, suspended=1):
    return {
        "applicable": True,
        "bridge_wakeup": bridge,
        "function_wakeup": {
            "enabled": enabled,
            "disabled": disabled,
            "unknown": unknown,
        },
        "function_runtime": {
            "active": active,
            "suspended": suspended,
            "unknown": unknown,
        },
        "reason": "wake.read_only_capability_observed",
    }


class WakeCaptureCompareTests(unittest.TestCase):
    def test_unchanged_aggregate_is_not_interpreted_as_suspend_safe(self):
        result = compare_wake_captures.compare_wake_diagnostics(
            capture(wake_diagnostics=wake()), capture(wake_diagnostics=wake())
        )

        self.assertEqual(result, {
            "state": "unchanged",
            "reason": "wake.aggregate_unchanged",
            "changes": [],
        })

    def test_changed_counts_remain_anonymous_and_categorical(self):
        result = compare_wake_captures.compare_wake_diagnostics(
            capture(wake_diagnostics=wake()),
            capture(wake_diagnostics=wake(bridge="disabled", enabled=1, disabled=2)),
        )

        self.assertEqual(result["state"], "changed")
        self.assertEqual(result["reason"], "wake.aggregate_changed")
        self.assertEqual(result["changes"], [
            "wake.bridge_capability_changed",
            "wake.function_wakeup_enabled_count_changed",
            "wake.function_wakeup_disabled_count_changed",
        ])
        self.assertNotIn("0000:", repr(result))

    def test_missing_or_inapplicable_evidence_is_inconclusive(self):
        self.assertEqual(
            compare_wake_captures.compare_wake_diagnostics(
                capture(wake_diagnostics=None), capture(wake_diagnostics=wake())
            )["reason"],
            "wake.before_unavailable",
        )
        without_topology = wake()
        without_topology["applicable"] = False
        self.assertEqual(
            compare_wake_captures.compare_wake_diagnostics(
                capture(wake_diagnostics=without_topology), capture(wake_diagnostics=wake())
            )["reason"],
            "wake.topology_unverified",
        )

    def test_load_revalidates_saved_capture_before_comparison(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "capture.json"
            path.write_text(json.dumps(capture(wake_diagnostics=wake())), encoding="utf-8")
            loaded = compare_wake_captures.load_capture(path)
            self.assertEqual(loaded["wake_diagnostics"]["bridge_wakeup"], "enabled")

            invalid = capture(wake_diagnostics=wake())
            invalid["wake_diagnostics"]["identity"] = "private"
            path.write_text(json.dumps(invalid), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "wake diagnostics"):
                compare_wake_captures.load_capture(path)


if __name__ == "__main__":
    unittest.main()
