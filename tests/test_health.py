from __future__ import annotations

import json
import sys
import unittest
from dataclasses import replace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from hdm.domain.control_plane import PlacementState  # noqa: E402
from hdm.domain.health import (  # noqa: E402
    HealthComponent,
    HealthComponentObservation,
    HealthEvidenceState,
    HealthState,
    assess_health,
    assess_snapshot_health,
)
from hdm.domain.models import (  # noqa: E402
    Confidence,
    EgpuLinkObservation,
    EgpuLinkState,
)
from hdm.domain.serialization import snapshot_from_dict  # noqa: E402


FIXTURES = ROOT / "tests" / "fixtures"


def fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class HealthAggregationTests(unittest.TestCase):
    def test_ready_components_are_ready(self):
        health = assess_health(
            (
                HealthComponentObservation(
                    HealthComponent.DISPLAY, HealthEvidenceState.READY
                ),
                HealthComponentObservation(
                    HealthComponent.SESSION, HealthEvidenceState.READY
                ),
            )
        )
        self.assertEqual(health.state, HealthState.READY)
        self.assertEqual(health.blockers, ())

    def test_unknown_evidence_requires_attention(self):
        health = assess_health(
            (
                HealthComponentObservation(
                    HealthComponent.DISPLAY, HealthEvidenceState.UNKNOWN
                ),
            )
        )
        self.assertEqual(health.state, HealthState.ATTENTION_REQUIRED)
        self.assertEqual(health.blockers, ("health.display_unknown",))

    def test_degraded_evidence_wins_over_recovering(self):
        health = assess_health(
            (
                HealthComponentObservation(
                    HealthComponent.DISPLAY, HealthEvidenceState.RECOVERING
                ),
                HealthComponentObservation(
                    HealthComponent.STORAGE, HealthEvidenceState.DEGRADED
                ),
            )
        )
        self.assertEqual(health.state, HealthState.DEGRADED)
        self.assertEqual(health.blockers, ("health.storage_degraded",))

    def test_duplicate_component_fails_closed(self):
        health = assess_health(
            (
                HealthComponentObservation(
                    HealthComponent.DISPLAY, HealthEvidenceState.READY
                ),
                HealthComponentObservation(
                    HealthComponent.DISPLAY, HealthEvidenceState.READY
                ),
            )
        )
        self.assertEqual(health.state, HealthState.ATTENTION_REQUIRED)
        self.assertEqual(health.blockers, ("health.duplicate_component",))

    def test_portable_fixture_has_currently_observed_ready_health(self):
        health = assess_snapshot_health(
            snapshot_from_dict(fixture("portable.json")), PlacementState.PORTABLE
        )
        self.assertEqual(health.state, HealthState.READY)

    def test_external_placement_never_claims_link_health_without_collector(self):
        health = assess_snapshot_health(
            snapshot_from_dict(fixture("tv-docked.json")), PlacementState.DOCKED_EGPU
        )
        self.assertEqual(health.state, HealthState.ATTENTION_REQUIRED)
        self.assertIn("health.egpu_link_unknown", health.blockers)

    def test_observed_link_up_completes_current_health_scope(self):
        snapshot = replace(
            snapshot_from_dict(fixture("tv-docked.json")),
            egpu_link=EgpuLinkObservation(
                True, EgpuLinkState.UP, Confidence.OBSERVED, "egpu.link_observed"
            ),
        )
        health = assess_snapshot_health(snapshot, PlacementState.DOCKED_EGPU)
        self.assertEqual(health.state, HealthState.READY)

    def test_storage_use_is_degraded(self):
        value = fixture("tv-docked.json")
        value["disconnect_readiness"]["storage_in_use"] = True
        health = assess_snapshot_health(
            snapshot_from_dict(value), PlacementState.DOCKED_EGPU
        )
        self.assertEqual(health.state, HealthState.DEGRADED)
        self.assertIn("health.storage_degraded", health.blockers)


if __name__ == "__main__":
    unittest.main()
