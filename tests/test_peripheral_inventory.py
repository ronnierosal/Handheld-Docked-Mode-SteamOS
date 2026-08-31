from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from hdm.adapters.steamos.peripherals import (  # noqa: E402
    PeripheralIdentityHints,
    SteamOsPeripheralInventory,
    SteamOsPeripheralObservationAdapter,
)


def write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


class PeripheralInventoryTests(unittest.TestCase):
    def _inventory(self, root: Path):
        return SteamOsPeripheralInventory(
            input_root=root / "input", sound_root=root / "sound"
        )

    def test_read_only_inventory_hashes_gamepad_and_sound_nodes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(root / "input" / "event7" / "device" / "capabilities" / "key", f"{1 << 0x130:x}\n")
            write(root / "input" / "event2" / "device" / "capabilities" / "key", "0\n")
            (root / "sound" / "card3").mkdir(parents=True)
            inventory = self._inventory(root).scan()
            self.assertTrue(inventory.controller_complete)
            self.assertTrue(inventory.audio_complete)
            self.assertEqual(len(inventory.controller_bindings), 1)
            self.assertEqual(len(inventory.audio_bindings), 1)
            self.assertNotIn(str(root), repr(inventory))

    def test_unreadable_sources_fail_closed(self):
        inventory = SteamOsPeripheralInventory(
            input_root=Path("missing-input"), sound_root=Path("missing-sound")
        ).scan()
        self.assertFalse(inventory.controller_complete)
        self.assertFalse(inventory.audio_complete)
        self.assertEqual(inventory.controller_error, "controller.input_root_unreadable")
        self.assertEqual(inventory.audio_error, "audio.sound_root_unreadable")

    def test_default_adapter_exposes_no_actionable_identity_or_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(root / "input" / "event1" / "device" / "capabilities" / "key", f"{1 << 0x130:x}\n")
            (root / "sound" / "card0").mkdir(parents=True)
            observed = SteamOsPeripheralObservationAdapter(
                self._inventory(root),
                generation_factory=lambda: "peripheral-generation-a",
                sample_factory=lambda: "peripheral-sample-a",
            ).observe()
            self.assertFalse(observed.controller.exact)
            self.assertFalse(observed.audio.exact)
            self.assertFalse(observed.controller.external_input_verified)
            self.assertFalse(observed.audio.external_output_verified)

    def test_exact_controller_mapping_still_never_claims_input_verified(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(root / "input" / "event1" / "device" / "capabilities" / "key", f"{1 << 0x130:x}\n")
            (root / "sound").mkdir()
            inventory = self._inventory(root)
            binding = inventory.scan().controller_bindings[0]
            observed = SteamOsPeripheralObservationAdapter(
                inventory,
                PeripheralIdentityHints(builtin_controller_binding=binding),
                generation_factory=lambda: "peripheral-generation-a",
                sample_factory=lambda: "peripheral-sample-a",
            ).observe()
            self.assertTrue(observed.controller.exact)
            self.assertTrue(observed.controller.builtin_available)
            self.assertFalse(observed.controller.builtin_input_verified)
            self.assertFalse(observed.controller.builtin_restore_verified)

    def test_default_semantic_generation_is_stable_but_samples_are_fresh(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(root / "input" / "event1" / "device" / "capabilities" / "key", f"{1 << 0x130:x}\n")
            (root / "sound" / "card0").mkdir(parents=True)
            adapter = SteamOsPeripheralObservationAdapter(self._inventory(root))
            first = adapter.observe()
            second = adapter.observe()
            self.assertEqual(first.generation, second.generation)
            self.assertNotEqual(first.sample_id, second.sample_id)
            write(root / "input" / "event9" / "device" / "capabilities" / "key", f"{1 << 0x130:x}\n")
            changed = adapter.observe()
            self.assertNotEqual(first.generation, changed.generation)


if __name__ == "__main__":
    unittest.main()
