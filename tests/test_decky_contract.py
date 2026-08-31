from __future__ import annotations

import ast
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DeckyContractTests(unittest.TestCase):
    def test_manifest_requests_root_for_protected_procfs_read(self):
        manifest = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["flags"], ["root"])
        self.assertEqual(manifest["api_version"], 1)
        self.assertIn("read-only", manifest["publish"]["description"].lower())

    def test_backend_exposes_only_snapshot_rpc(self):
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
        self.assertEqual(public_methods, {"get_snapshot"})

    def test_frontend_calls_only_snapshot_rpc(self):
        source = (ROOT / "src" / "backend.ts").read_text(encoding="utf-8")
        self.assertIn('callable<[], SnapshotPayload>("get_snapshot")', source)
        for forbidden in ("apply_transition", "restart_gamescope", "switch_display"):
            self.assertNotIn(forbidden, source.lower())


if __name__ == "__main__":
    unittest.main()
