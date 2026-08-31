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
from hdm.profiles.registry import (  # noqa: E402
    ProfileResolutionStatus,
    resolve_runtime_profiles,
    runtime_profile_diagnostics_to_dict,
)


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
        self.assertEqual(resolved.host_status, ProfileResolutionStatus.EXACT)
        self.assertEqual(resolved.egpu_status, ProfileResolutionStatus.EXACT)
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

    def test_exact_g1_resolution_requires_typed_identity_binding(self):
        value = json.loads((FIXTURES / "connected-internal.json").read_text())
        value["disconnect_readiness"]["egpu_stable_id"] = "gpd-g1:fedcba9876543210"
        mismatch = resolve_runtime_profiles(snapshot_from_dict(value))
        self.assertFalse(mismatch.exact_egpu)
        self.assertEqual(mismatch.egpu_status, ProfileResolutionStatus.UNKNOWN)
        self.assertEqual(mismatch.capabilities.display_handoff, CapabilitySupport.UNKNOWN)
        self.assertEqual(mismatch.capabilities.audio_handoff, CapabilitySupport.UNKNOWN)
        self.assertEqual(mismatch.capabilities.sleep_behavior.value, "untested")
        self.assertEqual(mismatch.capabilities.removal_behavior.value, "unknown")

        value = json.loads((FIXTURES / "connected-internal.json").read_text())
        value["gpus"][1]["stable_id"] = "gpd-g1:similar-name"
        value["disconnect_readiness"]["egpu_stable_id"] = "gpd-g1:similar-name"
        similar = resolve_runtime_profiles(snapshot_from_dict(value))
        self.assertFalse(similar.exact_egpu)
        self.assertEqual(similar.capabilities.display_handoff, CapabilitySupport.UNKNOWN)

    def test_diagnostics_keep_capability_axes_and_evidence_independent(self):
        diagnostics = runtime_profile_diagnostics_to_dict(
            resolve_runtime_profiles(observed("connected-internal.json")).diagnostics()
        )
        capabilities = {
            item["axis"]: item for item in diagnostics["capabilities"]
        }
        self.assertEqual(diagnostics["host"]["status"], "exact")
        self.assertEqual(diagnostics["egpu"]["status"], "exact")
        self.assertEqual(capabilities["egpu_transport"]["value"], "usb4")
        self.assertEqual(
            capabilities["external_display_output"]["confidence"], "verified"
        )
        self.assertEqual(capabilities["display_handoff"]["value"], "experimental")
        self.assertEqual(capabilities["audio_handoff"]["confidence"], "observed")
        self.assertEqual(
            capabilities["external_controller_promotion"]["value"], "unknown"
        )
        self.assertEqual(
            capabilities["sleep_behavior"]["value"],
            "disconnect_before_sleep_verified",
        )
        self.assertEqual(
            capabilities["removal_behavior"]["value"],
            "shutdown_before_disconnect",
        )

    def test_unknown_host_and_egpu_emit_no_mutation_capability(self):
        snapshot = observed(
            "ambiguous.json",
            host_profile="unknown",
            support_tier="unknown",
        )
        resolved = resolve_runtime_profiles(snapshot)
        self.assertFalse(resolved.exact_host)
        self.assertFalse(resolved.exact_egpu)
        self.assertEqual(resolved.host_status, ProfileResolutionStatus.UNKNOWN)
        self.assertEqual(resolved.egpu_status, ProfileResolutionStatus.UNKNOWN)
        self.assertEqual(resolved.capabilities.display_handoff, CapabilitySupport.UNKNOWN)
        self.assertEqual(resolved.capabilities.audio_handoff, CapabilitySupport.UNKNOWN)

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
