"""Validate a local D2 before/after evidence record without contacting the Ally.

The record consists of two already-saved, redacted read-only captures and two
already-verified validation artifacts. This local check proves only internal
provenance/continuity of those records; it cannot prove player presence, G1
disconnection, install success, UI usability, or authorize D2.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import remote_capture
from verify_d2_artifacts import verify_d2_artifacts


BOOT_ID_RE = re.compile(r"^[0-9a-f]{16}$")


def _is_read_only_capture(capture: dict[str, Any]) -> bool:
    if capture.get("schema_version") != 1:
        return False
    collector = capture.get("collector")
    if not isinstance(collector, dict) or (
        collector.get("read_only") is not True
        or collector.get("remote_files_written") is not False
        or collector.get("transport") != "ssh_stdin"
        or collector.get("execution_privilege")
        not in {"unprivileged", "root_read_only"}
    ):
        return False
    try:
        remote_capture._validate_safe_shape(capture)
    except ValueError:
        return False
    return True


def _captured_build_matches(
    capture: dict[str, Any], *, revision: str, version: str
) -> bool:
    plugin = capture.get("plugin")
    if not isinstance(plugin, dict) or plugin.get("present") is not True:
        return False
    build = plugin.get("build")
    return (
        isinstance(build, dict)
        and build.get("schema_version") == 1
        and plugin.get("version") == version
        and build.get("version") == version
        and build.get("revision") == revision
    )


def _boot_and_uptime(capture: dict[str, Any]) -> tuple[str, int] | None:
    system = capture.get("system")
    if not isinstance(system, dict):
        return None
    boot_id = system.get("boot_id_sha256")
    uptime = system.get("uptime_seconds")
    if not isinstance(boot_id, str) or not BOOT_ID_RE.fullmatch(boot_id):
        return None
    if type(uptime) is not int or uptime < 0:
        return None
    return boot_id, uptime


def verify_d2_evidence_record(
    candidate_directory: Path,
    rollback_directory: Path,
    before_capture: dict[str, Any],
    after_capture: dict[str, Any],
    *,
    rollback_revision_prefix: str,
) -> dict[str, object]:
    """Return only categorical local evidence-record consistency."""
    if not _is_read_only_capture(before_capture) or not _is_read_only_capture(after_capture):
        return {"state": "invalid", "reason": "d2.capture_schema_invalid"}
    artifacts = verify_d2_artifacts(
        candidate_directory,
        rollback_directory,
        rollback_revision_prefix=rollback_revision_prefix,
    )
    if artifacts.get("state") != "verified_for_supervised_review":
        return {"state": "invalid", "reason": "d2.artifact_pair_invalid"}
    candidate_revision = artifacts["candidate_revision"]
    rollback_revision = artifacts["rollback_revision"]
    if not isinstance(candidate_revision, str) or not isinstance(rollback_revision, str):
        return {"state": "invalid", "reason": "d2.artifact_pair_invalid"}

    candidate_version = artifacts.get("candidate_version")
    rollback_version = artifacts.get("rollback_version")
    if not isinstance(candidate_version, str) or not isinstance(rollback_version, str):
        return {"state": "invalid", "reason": "d2.artifact_pair_invalid"}
    if not _captured_build_matches(
        before_capture,
        revision=rollback_revision,
        version=rollback_version,
    ):
        return {"state": "invalid", "reason": "d2.before_capture_provenance_invalid"}
    if not _captured_build_matches(
        after_capture,
        revision=candidate_revision,
        version=candidate_version,
    ):
        return {"state": "invalid", "reason": "d2.after_capture_provenance_invalid"}

    before_system = _boot_and_uptime(before_capture)
    after_system = _boot_and_uptime(after_capture)
    if before_system is None or after_system is None:
        return {"state": "invalid", "reason": "d2.capture_continuity_invalid"}
    if before_system[0] != after_system[0] or after_system[1] < before_system[1]:
        return {"state": "invalid", "reason": "d2.capture_continuity_invalid"}
    return {"state": "verified_d2_evidence_record"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate_directory", type=Path)
    parser.add_argument("rollback_directory", type=Path)
    parser.add_argument("before_capture", type=Path)
    parser.add_argument("after_capture", type=Path)
    parser.add_argument("--rollback-revision-prefix", required=True)
    args = parser.parse_args()
    try:
        before = remote_capture.load_saved_capture(args.before_capture)
        after = remote_capture.load_saved_capture(args.after_capture)
    except (OSError, ValueError):
        print(json.dumps({"state": "invalid", "reason": "d2.capture_unreadable"}))
        return 1
    result = verify_d2_evidence_record(
        args.candidate_directory,
        args.rollback_directory,
        before,
        after,
        rollback_revision_prefix=args.rollback_revision_prefix,
    )
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("state") == "verified_d2_evidence_record" else 1


if __name__ == "__main__":
    raise SystemExit(main())
