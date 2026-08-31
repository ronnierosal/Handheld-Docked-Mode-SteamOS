from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from hdm.delivery.gamescope_wrapper import (  # noqa: E402
    MAX_CONFIG_BYTES,
    GamescopeLaunchConfig,
    _load_config,
    config_from_dict,
    config_to_dict,
    rewrite_gamescope_argv,
    select_launch_configuration,
)


BOOT_HASH = hashlib.sha256(b"boot").hexdigest()


def docked_config(**changes: str) -> GamescopeLaunchConfig:
    values = {
        "boot_id_sha256": BOOT_HASH,
        "target": "docked_egpu",
        "internal_connector": "eDP-1",
        "external_connector": "HDMI-A-1",
        "vendor_device": "1002:7480",
    }
    values.update(changes)
    return GamescopeLaunchConfig(**values)


class GamescopeConfigTests(unittest.TestCase):
    def test_round_trip_has_exact_shape_and_types(self):
        config = docked_config()
        self.assertEqual(config_from_dict(config_to_dict(config)), config)
        invalid = config_to_dict(config)
        invalid["extra"] = "unsafe"
        with self.assertRaisesRegex(ValueError, "shape"):
            config_from_dict(invalid)
        invalid = config_to_dict(config)
        invalid["schema_version"] = True
        with self.assertRaisesRegex(ValueError, "type"):
            config_from_dict(invalid)

    def test_docked_target_cannot_reuse_internal_connector(self):
        with self.assertRaisesRegex(ValueError, "incomplete"):
            docked_config(external_connector="eDP-1")

    def test_loader_rejects_oversized_and_symlinked_config(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "presentation.json"
            target.write_bytes(b"{" + b" " * MAX_CONFIG_BYTES + b"}")
            self.assertIsNone(_load_config(root))
            target.unlink()
            real = root / "real.json"
            real.write_text(json.dumps(config_to_dict(docked_config())), encoding="utf-8")
            try:
                target.symlink_to(real)
            except OSError:
                self.skipTest("file symlinks are unavailable on this host")
            self.assertIsNone(_load_config(root))


class GamescopeSelectionTests(unittest.TestCase):
    def test_exact_same_boot_docked_evidence_selects_external_gpu(self):
        self.assertEqual(
            select_launch_configuration(
                docked_config(),
                current_boot_id_sha256=BOOT_HASH,
                connected_connectors=("eDP-1", "HDMI-A-1"),
                internal_connectors=("eDP-1",),
                present_vendor_devices=("1002:0000", "1002:7480"),
            ),
            ("HDMI-A-1", "1002:7480"),
        )

    def test_stale_or_ambiguous_docked_evidence_falls_back_to_panel(self):
        cases = (
            {"current_boot_id_sha256": hashlib.sha256(b"other").hexdigest()},
            {"present_vendor_devices": ("1002:7480", "1002:7480")},
            {"connected_connectors": ("eDP-1",)},
        )
        defaults = {
            "current_boot_id_sha256": BOOT_HASH,
            "connected_connectors": ("eDP-1", "HDMI-A-1"),
            "internal_connectors": ("eDP-1",),
            "present_vendor_devices": ("1002:7480",),
        }
        for changes in cases:
            with self.subTest(changes=changes):
                self.assertEqual(
                    select_launch_configuration(docked_config(), **(defaults | changes)),
                    ("*,eDP-1", ""),
                )

    def test_no_unique_internal_panel_preserves_existing_output_selection(self):
        self.assertEqual(
            select_launch_configuration(
                None,
                current_boot_id_sha256=BOOT_HASH,
                connected_connectors=("HDMI-A-1",),
                internal_connectors=(),
                present_vendor_devices=(),
            ),
            ("", ""),
        )


class GamescopeRewriteTests(unittest.TestCase):
    def test_rewrite_deduplicates_managed_arguments_and_preserves_tail(self):
        self.assertEqual(
            rewrite_gamescope_argv(
                (
                    "-f",
                    "-O",
                    "old",
                    "--prefer-output=older",
                    "--prefer-vk-device",
                    "dead:beef",
                    "--",
                    "steam",
                    "-O",
                    "untouched",
                ),
                output_order="HDMI-A-1",
                vendor_device="1002:7480",
            ),
            (
                "-f",
                "-O",
                "HDMI-A-1",
                "--prefer-vk-device",
                "1002:7480",
                "--",
                "steam",
                "-O",
                "untouched",
            ),
        )

    def test_fail_closed_rewrite_preserves_output_but_clears_gpu_selector(self):
        self.assertEqual(
            rewrite_gamescope_argv(
                ("-O", "existing", "--prefer-vk-device=1002:7480"),
                output_order="",
            ),
            ("-O", "existing"),
        )

    def test_incomplete_managed_argument_is_rejected(self):
        for value in (("-O",), ("--prefer-vk-device",)):
            with self.subTest(value=value), self.assertRaisesRegex(
                ValueError, "incomplete"
            ):
                rewrite_gamescope_argv(value, output_order="")


if __name__ == "__main__":
    unittest.main()
