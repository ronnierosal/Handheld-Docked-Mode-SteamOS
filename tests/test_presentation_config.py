from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from hdm.delivery.presentation_config import PresentationConfigStore  # noqa: E402
from hdm.domain.control_plane import PlacementState, TransitionBinding  # noqa: E402
from hdm.domain.serialization import snapshot_from_dict  # noqa: E402


FIXTURES = ROOT / "tests" / "fixtures"
BOOT_ID = "12345678-1234-1234-1234-123456789abc"


def snapshot():
    value = json.loads((FIXTURES / "tv-docked.json").read_text(encoding="utf-8"))
    return snapshot_from_dict(value)


def binding(**changes: str) -> TransitionBinding:
    values = {
        "host_profile_id": "asus-rog-ally-x",
        "egpu_profile_id": "gpd-g1-rx7600mxt-titan-ridge",
        "egpu_stable_id": "gpd-g1:0123456789abcdef",
        "internal_gpu_stable_id": "internal-gpu",
        "external_gpu_stable_id": "gpd-g1:0123456789abcdef",
        "internal_display_stable_id": "internal-panel",
        "external_display_stable_id": "external-tv",
    }
    values.update(changes)
    return TransitionBinding(**values)


class PresentationConfigStoreTests(unittest.TestCase):
    def test_writes_and_loads_docked_and_portable_targets(self):
        with tempfile.TemporaryDirectory() as directory:
            store = PresentationConfigStore(Path(directory))
            docked = store.write_target(
                target=PlacementState.DOCKED_EGPU,
                binding=binding(),
                snapshot=snapshot(),
                boot_id=BOOT_ID,
            )
            self.assertEqual(docked.external_connector, "HDMI-A-1")
            self.assertEqual(docked.vendor_device, "1002:7480")
            self.assertEqual(
                docked.egpu_binding_sha256,
                hashlib.sha256(
                    f"{BOOT_ID}:{binding().egpu_stable_id}".encode("utf-8")
                ).hexdigest(),
            )
            self.assertNotIn(
                BOOT_ID,
                (Path(directory) / "presentation.json").read_text(encoding="utf-8"),
            )
            self.assertNotIn(
                binding().egpu_stable_id,
                (Path(directory) / "presentation.json").read_text(encoding="utf-8"),
            )
            self.assertEqual(store.load(), docked)

            docked_igpu = store.write_target(
                target=PlacementState.DOCKED_IGPU,
                binding=binding(),
                snapshot=snapshot(),
                boot_id=BOOT_ID,
            )
            self.assertEqual(docked_igpu.target, "docked_igpu")
            self.assertEqual(docked_igpu.external_connector, "HDMI-A-1")
            self.assertEqual(docked_igpu.vendor_device, "1002:0000")
            self.assertEqual(docked_igpu.egpu_binding_sha256, docked.egpu_binding_sha256)
            self.assertEqual(store.load(), docked_igpu)

            portable = store.write_target(
                target=PlacementState.PORTABLE,
                binding=binding(),
                snapshot=snapshot(),
                boot_id=BOOT_ID,
            )
            self.assertEqual(portable.internal_connector, "eDP-1")
            self.assertEqual(portable.external_connector, "")
            self.assertEqual(portable.egpu_binding_sha256, "")
            self.assertEqual(store.load(), portable)

    def test_rejects_changed_identity_invalid_boot_and_unsupported_target(self):
        with tempfile.TemporaryDirectory() as directory:
            store = PresentationConfigStore(Path(directory))
            with self.assertRaisesRegex(ValueError, "identities changed"):
                store.write_target(
                    target=PlacementState.DOCKED_EGPU,
                    binding=binding(external_display_stable_id="other"),
                    snapshot=snapshot(),
                    boot_id=BOOT_ID,
                )
            with self.assertRaisesRegex(ValueError, "boot identity"):
                store.write_target(
                    target=PlacementState.PORTABLE,
                    binding=binding(),
                    snapshot=snapshot(),
                    boot_id="",
                )
            with self.assertRaisesRegex(ValueError, "unsupported"):
                store.write_target(
                    target=PlacementState.BOOSTED_HANDHELD,
                    binding=binding(),
                    snapshot=snapshot(),
                    boot_id=BOOT_ID,
                )

    def test_relative_or_symlink_root_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "absolute"):
            PresentationConfigStore(Path("relative"))
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            real = parent / "real"
            real.mkdir()
            link = parent / "link"
            try:
                link.symlink_to(real, target_is_directory=True)
            except OSError:
                self.skipTest("directory symlinks are unavailable on this host")
            with self.assertRaisesRegex(ValueError, "real directory"):
                PresentationConfigStore(link).load()


if __name__ == "__main__":
    unittest.main()
