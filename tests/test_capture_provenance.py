from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from compare_capture_provenance import (  # noqa: E402
    compare_capture_provenance,
)
from remote_capture_payload import CRITICAL_FILES  # noqa: E402


class CaptureProvenanceTests(unittest.TestCase):
    @staticmethod
    def _capture() -> dict[str, object]:
        hashes = {
            path.as_posix(): hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            for path in CRITICAL_FILES
        }
        version = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))["version"]
        return {
            "plugin": {
                "present": True,
                "version": version,
                "critical_file_sha256": hashes,
            }
        }

    def test_matching_fixed_checkout_files_are_categorical_only(self):
        result = compare_capture_provenance(self._capture())
        self.assertEqual(result, {"state": "match", "reason": "provenance.fixed_files_match"})

    def test_version_or_file_mismatch_never_reports_a_match(self):
        version = self._capture()
        version["plugin"] = dict(version["plugin"], version="0.0.0")
        self.assertEqual(
            compare_capture_provenance(version)["reason"],
            "provenance.version_mismatch",
        )
        file = self._capture()
        hashes = dict(file["plugin"]["critical_file_sha256"])
        hashes["main.py"] = "0" * 64
        file["plugin"] = dict(file["plugin"], critical_file_sha256=hashes)
        result = compare_capture_provenance(file)
        self.assertEqual(result["reason"], "provenance.fixed_files_mismatch")
        self.assertEqual(result["mismatched_file_count"], 1)

    def test_missing_plugin_or_incomplete_capture_remains_inconclusive(self):
        self.assertEqual(
            compare_capture_provenance({})["reason"],
            "provenance.plugin_unavailable",
        )
        incomplete = self._capture()
        incomplete["plugin"] = dict(
            incomplete["plugin"], critical_file_sha256={}
        )
        self.assertEqual(
            compare_capture_provenance(incomplete)["reason"],
            "provenance.capture_incomplete",
        )
