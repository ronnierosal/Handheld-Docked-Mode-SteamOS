"""Compare one validated redacted Ally capture with this local checkout.

The tool performs local reads only. It never opens SSH, prints file hashes, or
changes the handheld. A match proves only that this checkout's fixed files
match the captured installed plugin files; it is not a hardware validation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import remote_capture
from remote_capture_payload import CRITICAL_FILES


ROOT = Path(__file__).resolve().parents[1]
HASH_RE = frozenset("0123456789abcdef")
REVISION_RE = re.compile(r"^[0-9a-f]{40}$")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(64 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _local_version(root: Path) -> str:
    try:
        value = json.loads((root / "package.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return ""
    version = value.get("version") if isinstance(value, dict) else None
    return version if isinstance(version, str) and 0 < len(version) <= 32 else ""


def _valid_hash(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= HASH_RE


def _local_checkout_revision(root: Path) -> str:
    """Return HEAD only when the local tracked checkout is clean."""
    try:
        for command in (("git", "diff", "--quiet"), ("git", "diff", "--cached", "--quiet")):
            result = subprocess.run(command, cwd=root, check=False, capture_output=True)
            if result.returncode == 1:
                return "uncommitted"
            if result.returncode != 0:
                return "unavailable"
        result = subprocess.run(
            ("git", "rev-parse", "HEAD"),
            cwd=root,
            check=False,
            text=True,
            capture_output=True,
        )
    except OSError:
        return "unavailable"
    revision = result.stdout.strip() if result.returncode == 0 else ""
    return revision if REVISION_RE.fullmatch(revision) else "unavailable"


def _compare_build_revision(
    plugin: dict[str, Any], *, checkout_revision: str
) -> dict[str, object] | None:
    """Return a categorical build mismatch/inconclusive result, or None to continue."""
    build = plugin.get("build")
    if build is None:
        return None
    if not isinstance(build, dict):
        return {"state": "inconclusive", "reason": "provenance.capture_build_invalid"}
    revision = build.get("revision")
    if revision == "uncommitted":
        return {"state": "inconclusive", "reason": "provenance.capture_build_uncommitted"}
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{12}", revision):
        return {"state": "inconclusive", "reason": "provenance.capture_build_unavailable"}
    if not REVISION_RE.fullmatch(checkout_revision):
        return {"state": "inconclusive", "reason": "provenance.checkout_revision_unavailable"}
    if revision != checkout_revision[:12]:
        return {"state": "mismatch", "reason": "provenance.build_revision_mismatch"}
    return None


def compare_capture_provenance(
    capture: dict[str, Any],
    *,
    source_root: Path = ROOT,
    checkout_revision: str | None = None,
) -> dict[str, object]:
    """Return only categorical installed-versus-checkout provenance evidence."""
    plugin = capture.get("plugin")
    if not isinstance(plugin, dict) or plugin.get("present") is not True:
        return {"state": "inconclusive", "reason": "provenance.plugin_unavailable"}
    captured_hashes = plugin.get("critical_file_sha256")
    expected_paths = tuple(path.as_posix() for path in CRITICAL_FILES)
    if (
        not isinstance(captured_hashes, dict)
        or set(captured_hashes) != set(expected_paths)
        or not all(_valid_hash(captured_hashes[path]) for path in expected_paths)
    ):
        return {"state": "inconclusive", "reason": "provenance.capture_incomplete"}
    root = source_root.resolve()
    if not root.is_dir():
        return {"state": "inconclusive", "reason": "provenance.checkout_unavailable"}
    version = _local_version(root)
    if not version:
        return {"state": "inconclusive", "reason": "provenance.checkout_manifest_unreadable"}
    if plugin.get("version") != version:
        return {"state": "mismatch", "reason": "provenance.version_mismatch"}
    build_result = _compare_build_revision(
        plugin,
        checkout_revision=(
            checkout_revision
            if checkout_revision is not None
            else _local_checkout_revision(root)
        ),
    )
    if build_result is not None:
        return build_result
    local_hashes: dict[str, str] = {}
    for relative in CRITICAL_FILES:
        path = root / relative
        if not path.is_file():
            return {"state": "inconclusive", "reason": "provenance.checkout_file_missing"}
        try:
            local_hashes[relative.as_posix()] = _sha256(path)
        except OSError:
            return {"state": "inconclusive", "reason": "provenance.checkout_file_unreadable"}
    mismatch_count = sum(
        local_hashes[path] != captured_hashes[path] for path in expected_paths
    )
    if mismatch_count:
        return {
            "state": "mismatch",
            "reason": "provenance.fixed_files_mismatch",
            "mismatched_file_count": mismatch_count,
        }
    return {"state": "match", "reason": "provenance.fixed_files_match"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path, help="saved remote capture")
    args = parser.parse_args()
    try:
        result = compare_capture_provenance(
            remote_capture.load_saved_capture(args.capture)
        )
    except (OSError, ValueError) as error:
        print(f"Provenance comparison failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
