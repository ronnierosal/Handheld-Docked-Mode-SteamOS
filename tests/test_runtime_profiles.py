from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from hdm.domain.control_plane import CapabilitySupport, PlacementState  # noqa: E402
from hdm.domain.manual_transition import evidence_from_snapshot  # noqa: E402
from hdm.domain.serialization import snapshot_from_dict  # noqa: E402
from hdm.profiles.registry import resolve_runtime_profiles  # noqa: E402


FIXTURES = ROOT / "tests" / "fixtures"


def observed(name: str, **changes):
    value = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    value.update(changes)
    for gpu in value["gpus"]:
        if gpu["role"] == "external":
            gpu["stable_id"] = "gpd-g1:0123456789abcdef"
    if value["gamescope"].get("render_gpu_stable_id", "").startswith("gpd-g1"):
        value["gamescope"]["render_gpu_stable_id"] = "gpd-g1:0123456789abcdef"
    return snapshot_from_dict(value)


class RuntimeProfileTests(unittest.TestCase):
    def test_exact_snapshot_resolves_ally_g1_without_promoting_experimental(self):
        snapshot = observed("connected-internal.json")
        resolved = resolve_runtime_profiles(snapshot)
        self.assertTrue(resolved.exact_host)
        self.assertTrue(resolved.exact_egpu)
        self.assertEqual(
            resolved.capabilities.display_handoff,
            CapabilitySupport.EXPERIMENTAL,
        )
        evidence = evidence_from_snapshot(
            snapshot,
            observed_generation="generation-1",
            capabilities=resolved.capabilities,
        )
        self.assertEqual(evidence.host_profile_id, "asus-rog-ally-x")
        self.assertEqual(evidence.egpu_stable_id, resolved.egpu_stable_id)
        self.assertTrue(evidence.source_recovery_ready_verified)
        self.assertIsNotNone(evidence.binding())

    def test_unknown_or_ambiguous_identity_gets_no_g1_capabilities(self):
        value = observed("connected-internal.json", support_tier="experimental")
        resolved = resolve_runtime_profiles(value)
        self.assertFalse(resolved.exact_egpu)
        self.assertEqual(resolved.capabilities.egpu_support, CapabilitySupport.VERIFIED)
        self.assertEqual(resolved.capabilities.display_handoff, CapabilitySupport.UNKNOWN)

    def test_docked_source_builds_a_recoverable_exact_binding(self):
        snapshot = observed("tv-docked.json")
        resolved = resolve_runtime_profiles(snapshot)
        evidence = evidence_from_snapshot(
            snapshot,
            observed_generation="generation-2",
            capabilities=resolved.capabilities,
        )
        self.assertTrue(evidence.source_recovery_ready_verified)
        self.assertEqual(evidence.external_display_stable_id, "external-tv")

    def test_missing_internal_fallback_keeps_recovery_unverified(self):
        snapshot = observed("connected-internal.json")
        snapshot = snapshot_from_dict(
            {
                **json.loads((FIXTURES / "connected-internal.json").read_text()),
                "gpus": [
                    {
                        **gpu,
                        "stable_id": "gpd-g1:0123456789abcdef",
                    }
                    for gpu in json.loads(
                        (FIXTURES / "connected-internal.json").read_text()
                    )["gpus"]
                    if gpu["role"] == "external"
                ],
            }
        )
        resolved = resolve_runtime_profiles(snapshot)
        evidence = evidence_from_snapshot(
            snapshot,
            observed_generation="generation-3",
            capabilities=resolved.capabilities,
        )
        self.assertFalse(evidence.source_recovery_ready_verified)
        self.assertIsNone(evidence.binding())


if __name__ == "__main__":
    unittest.main()
