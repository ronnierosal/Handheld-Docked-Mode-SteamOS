from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from verify_d2_artifacts import main, verify_d2_artifacts  # noqa: E402


ARCHIVE_NAME = "HandheldDockMode-0.2.0.zip"


def artifact(directory: Path, revision: str) -> None:
    archive = directory / ARCHIVE_NAME
    with zipfile.ZipFile(archive, "w") as value:
        value.writestr("HandheldDockMode/plugin.json", "{}")
        value.writestr(
            "HandheldDockMode/package.json", json.dumps({"version": "0.2.0"})
        )
        value.writestr(
            "HandheldDockMode/build_info.json",
            json.dumps(
                {"schema_version": 1, "version": "0.2.0", "revision": revision}
            ),
        )
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (directory / "source-revision.txt").write_text(f"{revision}\n", encoding="utf-8")
    (directory / "SHA256SUMS.txt").write_text(
        f"{digest}  out/{ARCHIVE_NAME}\n", encoding="utf-8"
    )


class D2ArtifactReadinessTests(unittest.TestCase):
    def test_verified_pair_is_only_ready_for_supervised_review(self):
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            candidate = root / "candidate"
            rollback = root / "rollback"
            candidate.mkdir()
            rollback.mkdir()
            artifact(candidate, "a" * 40)
            artifact(rollback, "b" * 40)
            self.assertEqual(
                verify_d2_artifacts(
                    candidate, rollback, rollback_revision_prefix="b" * 12
                ),
                {
                    "state": "verified_for_supervised_review",
                    "candidate_revision": "a" * 12,
                    "rollback_revision": "b" * 12,
                },
            )

    def test_invalid_candidate_or_rollback_stops_without_leaking_details(self):
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            candidate = root / "candidate"
            rollback = root / "rollback"
            candidate.mkdir()
            rollback.mkdir()
            artifact(candidate, "a" * 40)
            artifact(rollback, "b" * 40)
            self.assertEqual(
                verify_d2_artifacts(
                    candidate, rollback, rollback_revision_prefix="c" * 12
                ),
                {"state": "invalid", "reason": "d2.rollback_artifact_invalid"},
            )
            (candidate / "SHA256SUMS.txt").unlink()
            self.assertEqual(
                verify_d2_artifacts(
                    candidate, rollback, rollback_revision_prefix="b" * 12
                ),
                {"state": "invalid", "reason": "d2.candidate_artifact_invalid"},
            )

    def test_command_requires_valid_pair(self):
        with patch.object(
            sys,
            "argv",
            [
                "verify_d2_artifacts.py",
                "relative-candidate",
                "relative-rollback",
                "--rollback-revision-prefix",
                "a" * 12,
            ],
        ):
            self.assertEqual(main(), 1)


if __name__ == "__main__":
    unittest.main()
