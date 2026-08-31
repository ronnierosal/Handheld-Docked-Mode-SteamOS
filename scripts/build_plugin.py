"""Create a deterministic Decky plugin archive from verified build outputs."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "out" / "HandheldDockMode-0.1.0.zip"
TOP_LEVEL_FILES = (
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "main.py",
    "package.json",
    "plugin.json",
)


def included_files() -> tuple[Path, ...]:
    paths = [ROOT / relative for relative in TOP_LEVEL_FILES]
    paths.append(ROOT / "dist" / "index.js")
    paths.append(ROOT / "dist" / "index.js.map")
    paths.extend(
        path
        for path in sorted((ROOT / "backend" / "hdm").rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    )
    return tuple(paths)


def main() -> int:
    manifest = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))
    if manifest.get("flags") != ["root"]:
        raise SystemExit("Refusing to package a manifest without the root delivery flag")
    files = included_files()
    missing = [str(path.relative_to(ROOT)) for path in files if not path.is_file()]
    if missing:
        raise SystemExit("Missing package inputs: " + ", ".join(missing))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            info = zipfile.ZipInfo(path.relative_to(ROOT).as_posix())
            info.date_time = (2026, 1, 1, 0, 0, 0)
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED)
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
