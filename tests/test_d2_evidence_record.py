from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from verify_d2_evidence_record import verify_d2_evidence_record  # noqa: E402


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


def capture(revision: str, *, boot: str = "a" * 16, uptime: int = 10) -> dict[str, object]:
    return {
        "schema_version": 1,
        "collector": {
            "read_only": True,
            "remote_files_written": False,
            "transport": "ssh_stdin",
            "execution_privilege": "unprivileged",
        },
        "system": {"boot_id_sha256": boot, "uptime_seconds": uptime},
        "plugin": {
            "present": True,
            "version": "0.2.0",
            "build": {"schema_version": 1, "version": "0.2.0", "revision": revision},
        },
    }


class D2EvidenceRecordTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.candidate = root / "candidate"
        self.rollback = root / "rollback"
        self.candidate.mkdir()
        self.rollback.mkdir()
        artifact(self.candidate, "a" * 40)
        artifact(self.rollback, "b" * 40)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def verify(self, before: dict[str, object], after: dict[str, object]) -> dict[str, object]:
        return verify_d2_evidence_record(
            self.candidate,
            self.rollback,
            before,
            after,
            rollback_revision_prefix="b" * 12,
        )

    def test_matching_read_only_before_after_record_is_not_a_d2_pass(self):
        self.assertEqual(
            self.verify(capture("b" * 12, uptime=10), capture("a" * 12, uptime=20)),
            {"state": "verified_d2_evidence_record"},
        )

    def test_changed_boot_or_build_mismatch_fails_closed(self):
        self.assertEqual(
            self.verify(
                capture("b" * 12), capture("a" * 12, boot="c" * 16, uptime=20)
            ),
            {"state": "invalid", "reason": "d2.capture_continuity_invalid"},
        )
        self.assertEqual(
            self.verify(capture("b" * 12), capture("c" * 12, uptime=20)),
            {"state": "invalid", "reason": "d2.after_capture_provenance_invalid"},
        )

    def test_non_read_only_or_private_capture_is_rejected(self):
        unsafe = capture("b" * 12)
        unsafe["collector"] = dict(unsafe["collector"], read_only=False)
        self.assertEqual(
            self.verify(unsafe, capture("a" * 12, uptime=20)),
            {"state": "invalid", "reason": "d2.capture_schema_invalid"},
        )
        private = capture("b" * 12)
        private["system"] = dict(private["system"], hostname="private")
        self.assertEqual(
            self.verify(private, capture("a" * 12, uptime=20)),
            {"state": "invalid", "reason": "d2.capture_schema_invalid"},
        )


if __name__ == "__main__":
    unittest.main()
