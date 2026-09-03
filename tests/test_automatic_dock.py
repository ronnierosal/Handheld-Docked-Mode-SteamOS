from __future__ import annotations

import json
import sys
import unittest
from dataclasses import replace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from hdm.application.attach_readiness import (  # noqa: E402
    AttachReadinessStage,
    AttachReadinessStatus,
)
from hdm.application.automatic_dock import (  # noqa: E402
    AutomaticDockCoordinator,
    AutomaticDockStage,
)
from hdm.domain.models import Confidence, EgpuLinkObservation, EgpuLinkState  # noqa: E402
from hdm.domain.serialization import snapshot_from_dict  # noqa: E402
from hdm.ports.transition import VersionedObservation  # noqa: E402


FIXTURES = ROOT / "tests" / "fixtures"


def fixture(name: str):
    return snapshot_from_dict(json.loads((FIXTURES / name).read_text(encoding="utf-8")))


def current(name: str, generation: str = "generation-ready"):
    value = fixture(name)
    if name == "connected-internal.json":
        value = replace(
            value,
            egpu_link=EgpuLinkObservation(
                True, EgpuLinkState.UP, Confidence.OBSERVED, "egpu.link_observed"
            ),
        )
    return VersionedObservation(generation, value, f"sample-{generation}")


def readiness(stage: AttachReadinessStage, code: str) -> AttachReadinessStatus:
    return AttachReadinessStatus(stage, code, 1000)


class AutomaticDockCoordinatorTests(unittest.TestCase):
    def test_disabled_or_partial_hardware_never_requests_a_switch(self):
        coordinator = AutomaticDockCoordinator()
        ready = readiness(AttachReadinessStage.READY_IDLE, "attach.ready_idle")

        self.assertFalse(
            coordinator.update(
                enabled=False, readiness=ready, current=current("connected-internal.json")
            ).should_switch
        )
        partial = coordinator.update(
            enabled=True, readiness=ready, current=current("portable.json")
        )
        self.assertFalse(partial.should_switch)
        self.assertEqual(partial.status.stage, AutomaticDockStage.OBSERVING)

    def test_exact_ready_idle_attach_requests_once_until_absent(self):
        coordinator = AutomaticDockCoordinator()
        ready = readiness(AttachReadinessStage.READY_IDLE, "attach.ready_idle")
        attached = current("connected-internal.json")

        first = coordinator.update(enabled=True, readiness=ready, current=attached)
        second = coordinator.update(enabled=True, readiness=ready, current=attached)

        self.assertTrue(first.should_switch)
        self.assertEqual(first.expected_generation, "generation-ready")
        self.assertFalse(second.should_switch)

        coordinator.update(
            enabled=True,
            readiness=readiness(AttachReadinessStage.IDLE, "attach.idle"),
            current=current("portable.json", "portable"),
        )
        again = coordinator.update(enabled=True, readiness=ready, current=attached)
        self.assertTrue(again.should_switch)

    def test_running_game_and_unready_link_wait_without_consuming_attempt(self):
        coordinator = AutomaticDockCoordinator()
        attached = current("connected-internal.json")
        waiting = coordinator.update(
            enabled=True,
            readiness=readiness(
                AttachReadinessStage.WAITING_FOR_LINK_HEALTH,
                "attach.link_unverified",
            ),
            current=attached,
        )
        running = coordinator.update(
            enabled=True,
            readiness=readiness(AttachReadinessStage.GAME_RUNNING, "attach.game_running"),
            current=attached,
        )

        self.assertFalse(waiting.should_switch)
        self.assertFalse(running.should_switch)
        self.assertEqual(running.status.stage, AutomaticDockStage.WAITING)

    def test_acknowledgement_or_opt_out_rearms_the_same_attachment(self):
        coordinator = AutomaticDockCoordinator()
        ready = readiness(AttachReadinessStage.READY_IDLE, "attach.ready_idle")
        attached = current("connected-internal.json")
        self.assertTrue(
            coordinator.update(
                enabled=True, readiness=ready, current=attached
            ).should_switch
        )

        coordinator.reset_after_acknowledgement()
        self.assertTrue(
            coordinator.update(
                enabled=True, readiness=ready, current=attached
            ).should_switch
        )
        coordinator.update(enabled=False, readiness=ready, current=attached)
        self.assertTrue(
            coordinator.update(
                enabled=True, readiness=ready, current=attached
            ).should_switch
        )


if __name__ == "__main__":
    unittest.main()
