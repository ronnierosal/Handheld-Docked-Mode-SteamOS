"""Verify local D2 candidate and rollback artifacts without contacting a device.

This is a bounded provenance gate only. It verifies two unpacked validation
artifacts and requires the rollback archive to carry the public revision label
previously recorded in a redacted capture. It cannot verify D2's player,
physical G1, install, lifecycle, or live-system preconditions.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from verify_validation_artifact import verify_validation_artifact


def verify_d2_artifacts(
    candidate_directory: Path,
    rollback_directory: Path,
    *,
    rollback_revision_prefix: str,
) -> dict[str, object]:
    """Return identity-minimized paired artifact readiness for supervised review."""
    candidate = verify_validation_artifact(candidate_directory)
    if candidate.get("state") != "verified":
        return {"state": "invalid", "reason": "d2.candidate_artifact_invalid"}

    rollback = verify_validation_artifact(
        rollback_directory,
        expected_revision_prefix=rollback_revision_prefix,
    )
    if rollback.get("state") != "verified":
        return {"state": "invalid", "reason": "d2.rollback_artifact_invalid"}

    return {
        "state": "verified_for_supervised_review",
        "candidate_revision": candidate["revision"],
        "candidate_version": candidate["version"],
        "rollback_revision": rollback["revision"],
        "rollback_version": rollback["version"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate_directory", type=Path)
    parser.add_argument("rollback_directory", type=Path)
    parser.add_argument(
        "--rollback-revision-prefix",
        required=True,
        help="12-character public rollback build revision label from a redacted capture",
    )
    args = parser.parse_args()
    result = verify_d2_artifacts(
        args.candidate_directory,
        args.rollback_directory,
        rollback_revision_prefix=args.rollback_revision_prefix,
    )
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("state") == "verified_for_supervised_review" else 1


if __name__ == "__main__":
    raise SystemExit(main())
