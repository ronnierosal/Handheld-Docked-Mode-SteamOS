"""Validate the Decky plugin layout and narrow 0.2 delivery contract."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path


REQUIRED_FILES = (
    "LICENSE",
    "backend/hdm/api.py",
    "backend/hdm/adapters/steamos/sleep_inhibitor.py",
    "backend/hdm/application/support_bundle.py",
    "backend/hdm/delivery/support_export.py",
    "backend/hdm/delivery/gamescope_wrapper.py",
    "backend/hdm/delivery/presentation_config.py",
    "bin/gamescope",
    "dist/index.js",
    "dist/index.js.map",
    "main.py",
    "package.json",
    "plugin.json",
)
FORBIDDEN_RPC_TERMS = (
    "apply_transition",
    "restart_gamescope",
    "set_gpu",
    "switch_display",
    "process_release",
    "signal_process",
    "force_close",
)


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    failures: list[str] = []
    for relative in REQUIRED_FILES:
        if not (root / relative).is_file():
            failures.append(f"missing {relative}")

    manifest_path = root / "plugin.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("flags") != ["root"]:
            failures.append("plugin.json must request only the root delivery flag")
        description = str(manifest.get("publish", {}).get("description", "")).lower()
        if "sleep safety" not in description:
            failures.append("plugin.json must describe the approved sleep-safety scope")

    main_path = root / "main.py"
    if main_path.is_file():
        tree = ast.parse(main_path.read_text(encoding="utf-8"), filename=str(main_path))
        plugin_classes = [
            node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Plugin"
        ]
        public_methods = {
            node.name
            for plugin in plugin_classes
            for node in plugin.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and not node.name.startswith("_")
        }
        allowed_methods = {
            "get_snapshot",
            "preview_support_bundle",
            "save_support_bundle",
        }
        if public_methods != allowed_methods:
            failures.append(
                "Decky backend RPCs must be limited to snapshot and approved support-bundle export"
            )

    delivery_sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (root / "main.py", root / "src" / "backend.ts")
        if path.is_file()
    ).lower()
    for term in FORBIDDEN_RPC_TERMS:
        if term in delivery_sources:
            failures.append(f"delivery layer contains forbidden mutation RPC term {term!r}")

    if failures:
        print("Plugin package check failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(
        "Plugin package check passed: diagnostics, approved support export, and sleep-guard lease only."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
