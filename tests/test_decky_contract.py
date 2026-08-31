from __future__ import annotations

import ast
import json
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

from scripts.build_plugin import OUTPUT, PLUGIN_DIRECTORY, archive_name  # noqa: E402


class DeckyContractTests(unittest.TestCase):
    def test_manifest_requests_root_for_observation_and_sleep_guard(self):
        manifest = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["flags"], ["root"])
        self.assertEqual(manifest["api_version"], 1)
        self.assertIn("sleep safety", manifest["publish"]["description"].lower())

    def test_backend_exposes_only_snapshot_and_support_bundle_rpcs(self):
        path = ROOT / "main.py"
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        plugin = next(
            node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Plugin"
        )
        public_methods = {
            node.name
            for node in plugin.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and not node.name.startswith("_")
        }
        self.assertEqual(
            public_methods,
            {"get_snapshot", "preview_support_bundle", "save_support_bundle"},
        )
        source = path.read_text(encoding="utf-8")
        self.assertNotIn("PosixProcessSignalAdapter", source)
        self.assertNotIn("ProcessReleaseApprovalStore", source)

    def test_frontend_calls_only_snapshot_and_support_bundle_rpcs(self):
        source = (ROOT / "src" / "backend.ts").read_text(encoding="utf-8")
        self.assertIn('callable<[], SnapshotPayload>("get_snapshot")', source)
        self.assertIn('"preview_support_bundle"', source)
        self.assertIn('"save_support_bundle"', source)
        for forbidden in (
            "apply_transition",
            "restart_gamescope",
            "switch_display",
            "process_release",
            "signal_process",
            "force_close",
        ):
            self.assertNotIn(forbidden, source.lower())

    def test_support_bundle_save_requires_a_preview_token_and_no_path(self):
        source = (ROOT / "src" / "backend.ts").read_text(encoding="utf-8")
        self.assertIn("callable<[string], SupportBundleSavePayload>", source)
        self.assertNotIn("saveSupportBundle = callable<[string, string]", source)

    def test_attempted_sleep_warning_requires_acknowledgement(self):
        source = (ROOT / "src" / "index.tsx").read_text(encoding="utf-8")
        self.assertIn("<ConfirmModal", source)
        self.assertIn('strOKButtonText="OK"', source)
        self.assertIn("bAlertDialog={true}", source)
        self.assertIn("bDisableBackgroundDismiss={true}", source)
        self.assertIn("bHideCloseIcon={true}", source)
        self.assertIn("BLOCKED_ATTEMPT_MODAL_DELAY_MS", source)
        self.assertIn("window.setTimeout", source)
        self.assertIn("window.clearTimeout", source)
        self.assertIn("bNeverPopOut: true", source)
        self.assertNotIn("    window,\n    { strTitle", source)
        self.assertEqual(
            source.count('    undefined,\n    { strTitle: "Handheld Dock Mode"'),
            2,
        )

    def test_decky_archive_has_one_top_level_plugin_directory(self):
        self.assertEqual(
            archive_name(ROOT / "plugin.json"),
            f"{PLUGIN_DIRECTORY}/plugin.json",
        )
        if OUTPUT.is_file():
            with zipfile.ZipFile(OUTPUT) as archive:
                top_levels = {name.split("/", 1)[0] for name in archive.namelist()}
                self.assertEqual(top_levels, {PLUGIN_DIRECTORY})
                self.assertIn(f"{PLUGIN_DIRECTORY}/plugin.json", archive.namelist())


if __name__ == "__main__":
    unittest.main()
