from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from verify_validation_artifact import main, verify_validation_artifact  # noqa: E402


REVISION = "a" * 40
ARCHIVE_NAME = "HandheldDockMode-0.2.0.zip"


class ValidationArtifactTests(unittest.TestCase):
    def _artifact(
        self,
        directory: Path,
        *,
        revision: str = REVISION,
        build_revision: str | None = None,
        version: str = "0.2.0",
    ) -> Path:
        archive = directory / ARCHIVE_NAME
        build_revision = build_revision or revision
        with zipfile.ZipFile(archive, "w") as value:
            value.writestr("HandheldDockMode/plugin.json", "{}")
            value.writestr(
                "HandheldDockMode/package.json", json.dumps({"version": version})
            )
            value.writestr(
                "HandheldDockMode/build_info.json",
                json.dumps(
                    {
                        "schema_version": 1,
                        "version": version,
                        "revision": build_revision,
                    }
                ),
            )
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        (directory / "source-revision.txt").write_text(f"{revision}\n", encoding="utf-8")
        (directory / "SHA256SUMS.txt").write_text(
            f"{digest}  out/{ARCHIVE_NAME}\n", encoding="utf-8"
        )
        return archive

    def test_exact_checksum_revision_and_embedded_build_are_verified(self):
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            self._artifact(root)
            self.assertEqual(
                verify_validation_artifact(root),
                {"state": "verified", "version": "0.2.0", "revision": "a" * 12},
            )

    def test_checksum_and_metadata_mismatches_fail_closed(self):
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            archive = self._artifact(root)
            archive.write_bytes(b"not a zip")
            self.assertEqual(
                verify_validation_artifact(root)["reason"],
                "artifact.checksum_mismatch",
            )

        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            self._artifact(root, build_revision="b" * 40)
            self.assertEqual(
                verify_validation_artifact(root)["reason"],
                "artifact.package_build_inconsistent",
            )

    def test_missing_ambiguous_or_unsafe_input_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            self.assertEqual(
                verify_validation_artifact(root)["reason"],
                "artifact.archive_ambiguous",
            )
            self._artifact(root)
            (root / "HandheldDockMode-0.2.1.zip").write_bytes(b"extra")
            self.assertEqual(
                verify_validation_artifact(root)["reason"],
                "artifact.archive_ambiguous",
            )
        self.assertEqual(
            verify_validation_artifact(Path("relative"))["reason"],
            "artifact.directory_invalid",
        )

    def test_command_fails_when_the_artifact_is_not_verified(self):
        with patch.object(sys, "argv", ["verify_validation_artifact.py", "relative"]):
            self.assertEqual(main(), 1)


if __name__ == "__main__":
    unittest.main()
