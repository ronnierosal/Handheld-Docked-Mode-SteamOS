from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from hdm.adapters.steamos.gamescope_user import GamescopeUserContext  # noqa: E402
from hdm.delivery.gamescope_integration import GamescopeIntegrationStore  # noqa: E402


class GamescopeIntegrationStoreTests(unittest.TestCase):
    def make_store(self, root: Path, *, effective_uid=0):
        user_uid = getattr(os, "getuid", lambda: 1000)()
        user_gid = getattr(os, "getgid", lambda: 1000)()
        home = root / "home" / "deck"
        home.mkdir(parents=True)
        plugin = root / "plugin"
        shim = plugin / "bin" / "gamescope"
        shim.parent.mkdir(parents=True)
        shim.write_text(
            '#!/usr/bin/python3\n"""Handheld Dock Mode Gamescope argument shim."""\n',
            encoding="utf-8",
        )
        if os.name != "nt":
            shim.chmod(0o755)
        user = GamescopeUserContext(
            "deck",
            user_uid,
            user_gid,
            home,
            Path("/run/user") / str(user_uid),
            Path("/run/user") / str(user_uid) / "bus",
        )
        owned = []
        store = GamescopeIntegrationStore(
            plugin_root=plugin,
            user=user,
            effective_uid=lambda: effective_uid,
            set_owner=lambda path, uid, gid: owned.append((path, uid, gid)),
        )
        return store, owned

    def test_activate_is_exact_idempotent_and_deactivate_is_reversible(self):
        with tempfile.TemporaryDirectory() as directory:
            store, owned = self.make_store(Path(directory))
            first = store.activate()
            self.assertTrue(first.ok)
            self.assertTrue(first.changed)
            self.assertTrue(store.target.is_file())
            self.assertIn("HDM_STATE_ROOT=", store.target.read_text(encoding="utf-8"))
            self.assertTrue(store.state_root.is_dir())
            self.assertTrue(owned)

            second = store.activate()
            self.assertTrue(second.ok)
            self.assertFalse(second.changed)

            removed = store.deactivate()
            self.assertTrue(removed.changed)
            self.assertFalse(store.target.exists())
            self.assertTrue(store.state_root.is_dir())

    def test_matching_dropin_with_missing_state_root_is_repaired_without_rewrite(self):
        with tempfile.TemporaryDirectory() as directory:
            store, _ = self.make_store(Path(directory))
            self.assertTrue(store.activate().ok)
            original = store.target.read_bytes()
            store.state_root.rmdir()
            repaired = store.activate()
            self.assertTrue(repaired.ok)
            self.assertTrue(repaired.changed)
            self.assertEqual(store.target.read_bytes(), original)

    def test_competing_path_override_fails_closed_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            store, _ = self.make_store(Path(directory))
            store.target.parent.mkdir(parents=True)
            conflict = store.target.parent / "50-egpubridge.conf"
            conflict.write_text(
                '[Service]\nEnvironment="PATH=/other/bin:/usr/bin"\n',
                encoding="utf-8",
            )
            result = store.activate()
            self.assertFalse(result.ok)
            self.assertEqual(result.status.error_code, "path_override_conflict")
            self.assertEqual(result.status.conflicts, ("50-egpubridge.conf",))
            self.assertFalse(store.target.exists())

    def test_unknown_environment_file_also_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            store, _ = self.make_store(Path(directory))
            store.target.parent.mkdir(parents=True)
            (store.target.parent / "other.conf").write_text(
                "[Service]\nEnvironmentFile=/somewhere/unknown\n", encoding="utf-8"
            )
            self.assertEqual(store.status().error_code, "path_override_conflict")

    def test_whitespace_and_pass_environment_path_conflicts_fail_closed(self):
        values = (
            "[Service]\nEnvironment = \"PATH=/other\"\n",
            "[Service]\nPassEnvironment = PATH\n",
            "[Service]\nUnsetEnvironment = PATH\n",
        )
        for value in values:
            with self.subTest(value=value), tempfile.TemporaryDirectory() as directory:
                store, _ = self.make_store(Path(directory))
                store.target.parent.mkdir(parents=True)
                (store.target.parent / "other.conf").write_text(value, encoding="utf-8")
                self.assertEqual(store.status().error_code, "path_override_conflict")

    def test_modified_managed_file_is_never_overwritten_or_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            store, _ = self.make_store(Path(directory))
            store.target.parent.mkdir(parents=True)
            store.target.write_text("user content\n", encoding="utf-8")
            self.assertEqual(store.activate().status.error_code, "managed_dropin_modified")
            self.assertFalse(store.deactivate().changed)
            self.assertEqual(store.target.read_text(encoding="utf-8"), "user content\n")

    def test_non_root_activation_and_missing_shim_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            store, _ = self.make_store(Path(directory), effective_uid=1000)
            self.assertEqual(store.activate().status.error_code, "root_required")
        with tempfile.TemporaryDirectory() as directory:
            store, _ = self.make_store(Path(directory))
            (store._plugin_root / "bin" / "gamescope").unlink()
            self.assertEqual(store.activate().status.error_code, "shim_unavailable")

    def test_symlinked_dropin_root_is_rejected_when_supported(self):
        with tempfile.TemporaryDirectory() as directory:
            store, _ = self.make_store(Path(directory))
            real = Path(directory) / "real"
            real.mkdir()
            store.target.parent.parent.mkdir(parents=True)
            try:
                store.target.parent.symlink_to(real, target_is_directory=True)
            except OSError:
                self.skipTest("directory symlinks are unavailable on this host")
            self.assertEqual(store.status().error_code, "inspection_failed")


if __name__ == "__main__":
    unittest.main()
