from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from hdm.domain.control_plane import (  # noqa: E402
    CapabilitySupport,
    PlacementState,
    PlannedStep,
    RemovalBehavior,
    TransitionPlan,
    UNKNOWN_EGPU_CAPABILITIES,
    UNKNOWN_HOST_CAPABILITIES,
    WorkflowState,
    compose_capabilities,
)
from hdm.domain.inference import infer_placement  # noqa: E402
from hdm.domain.serialization import snapshot_from_dict  # noqa: E402
from hdm.profiles.ally_x import CAPABILITIES as ALLY_X_CAPABILITIES  # noqa: E402
from hdm.profiles.gpd_g1 import CAPABILITIES as GPD_G1_CAPABILITIES  # noqa: E402


FIXTURES = ROOT / "tests" / "fixtures"


def fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class PlacementInferenceTests(unittest.TestCase):
    def test_existing_placements_map_without_changing_public_schema(self):
        cases = {
            "portable.json": PlacementState.PORTABLE,
            "boosted-handheld.json": PlacementState.BOOSTED_HANDHELD,
            "tv-docked.json": PlacementState.DOCKED_EGPU,
        }
        for name, expected in cases.items():
            with self.subTest(name=name):
                self.assertEqual(
                    infer_placement(snapshot_from_dict(fixture(name))), expected
                )

    def test_verified_internal_renderer_and_external_display_is_docked_igpu(self):
        value = fixture("tv-docked.json")
        value["gpus"][0]["selected_for_render"] = True
        value["gpus"][1]["selected_for_render"] = False
        value["gamescope"]["render_gpu_stable_id"] = value["gpus"][0]["stable_id"]
        value["gamescope"]["render_vendor_device"] = value["gpus"][0][
            "vendor_device"
        ]
        self.assertEqual(
            infer_placement(snapshot_from_dict(value)), PlacementState.DOCKED_IGPU
        )

    def test_unknown_evidence_never_claims_docked_igpu(self):
        value = fixture("tv-docked.json")
        value["gpus"][0]["selected_for_render"] = True
        value["gpus"][1]["selected_for_render"] = False
        value["gamescope"]["render_gpu_stable_id"] = value["gpus"][0]["stable_id"]
        value["displays"][1]["confidence"] = "unknown"
        self.assertEqual(
            infer_placement(snapshot_from_dict(value)), PlacementState.UNKNOWN
        )


class CapabilityTests(unittest.TestCase):
    def test_unknown_profiles_fail_closed(self):
        effective = compose_capabilities(
            UNKNOWN_HOST_CAPABILITIES, UNKNOWN_EGPU_CAPABILITIES
        )
        self.assertEqual(effective.display_handoff, CapabilitySupport.UNKNOWN)
        self.assertEqual(effective.audio_handoff, CapabilitySupport.UNKNOWN)
        self.assertFalse(effective.live_removal_allowed)

    def test_current_ally_g1_profile_does_not_allow_live_removal(self):
        effective = compose_capabilities(ALLY_X_CAPABILITIES, GPD_G1_CAPABILITIES)
        self.assertEqual(effective.display_handoff, CapabilitySupport.EXPERIMENTAL)
        self.assertEqual(effective.audio_handoff, CapabilitySupport.EXPERIMENTAL)
        self.assertEqual(
            effective.removal_behavior, RemovalBehavior.SHUTDOWN_BEFORE_DISCONNECT
        )
        self.assertFalse(effective.live_removal_allowed)


class TransitionContractTests(unittest.TestCase):
    def test_plan_rejects_duplicate_step_codes(self):
        with self.assertRaisesRegex(ValueError, "unique"):
            TransitionPlan(
                plan_id="plan-1",
                request_id="request-1",
                observed_generation="generation-1",
                from_placement=PlacementState.PORTABLE,
                target_placement=PlacementState.DOCKED_EGPU,
                workflow_state=WorkflowState.CONNECTING,
                steps=(
                    PlannedStep("observe", 1000),
                    PlannedStep("observe", 2000),
                ),
            )

    def test_step_deadline_must_be_positive(self):
        with self.assertRaisesRegex(ValueError, "positive"):
            PlannedStep("observe", 0)


if __name__ == "__main__":
    unittest.main()
