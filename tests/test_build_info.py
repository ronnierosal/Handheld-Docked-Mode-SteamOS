from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from hdm.delivery.build_info import load_public_build_info  # noqa: E402
from scripts.build_plugin import build_info_bytes  # noqa: E402


class BuildInfoTests(unittest.TestCase):
    def test_clean_revision_is_shortened_only_for_public_delivery(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            revision = "a" * 40
            (root / "build_info.json").write_bytes(build_info_bytes(revision))

            self.assertEqual(
                load_public_build_info(root),
                {"schema_version": 1, "version": "0.2.0", "revision": "a" * 12},
            )

    def test_uncommitted_and_invalid_metadata_never_claim_a_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "build_info.json").write_bytes(build_info_bytes("uncommitted"))
            self.assertEqual(load_public_build_info(root)["revision"], "uncommitted")

            (root / "build_info.json").write_text(
                json.dumps({"schema_version": 1, "version": "0.2.0", "revision": "not-a-commit"}),
                encoding="utf-8",
            )
            self.assertEqual(load_public_build_info(root)["revision"], "unavailable")

    def test_archive_metadata_refuses_invalid_revisions(self):
        with self.assertRaisesRegex(ValueError, "revision"):
            build_info_bytes("private-workstation-data")


if __name__ == "__main__":
    unittest.main()
