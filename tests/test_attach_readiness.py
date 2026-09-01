from __future__ import annotations

import json
import sys
import unittest
from dataclasses import replace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from hdm.application.attach_readiness import (  # noqa: E402
    AttachReadinessLifecycle,
    AttachReadinessStage,
    arm_attach_readiness,
    observe_attach_readiness,
)
from hdm.application.topology_event_detection import detect_topology_event  # noqa: E402
from hdm.domain.models import (  # noqa: E402
    Confidence,
    DisplayKind,
    EgpuLinkObservation,
    EgpuLinkState,
    GameState,
)
from hdm.domain.serialization import snapshot_from_dict  # noqa: E402
from hdm.ports.transition import VersionedObservation  # noqa: E402


FIXTURES = ROOT / "tests" / "fixtures"


def snapshot(name: str):
    return snapshot_from_dict(json.loads((FIXTURES / name).read_text(encoding="utf-8")))


def observed(generation: str, sample: str, value):
    return VersionedObservation(generation, value, sample)


def link_up(value):
    return replace(
        value,
        egpu_link=EgpuLinkObservation(
            True, EgpuLinkState.UP, Confidence.OBSERVED, "egpu.link_observed"
        ),
    )


class AttachReadinessTests(unittest.TestCase):
    def _watch(self):
        before = observed("portable", "sample-a", snapshot("portable.json"))
        attached = observed("attached", "sample-b", snapshot("connected-internal.json"))
        detection = detect_topology_event(before, attached)
        watch = arm_attach_readiness(detection, attached)
        self.assertIsNotNone(watch)
        return watch, attached

    def test_exact_attached_idle_tv_is_readiness_only(self):
        watch, attached = self._watch()

        result = observe_attach_readiness(
            watch,
            observed(attached.generation, "sample-c", link_up(attached.snapshot)),
        )

        self.assertEqual(result.stage, AttachReadinessStage.READY_IDLE)
        self.assertEqual(result.code, "attach.ready_idle")

    def test_reused_sample_waits_and_changed_identity_fails_closed(self):
        watch, attached = self._watch()
        settling = observe_attach_readiness(watch, attached)
        self.assertEqual(settling.stage, AttachReadinessStage.SETTLING)

        changed = replace(
            attached.snapshot,
            gpus=tuple(
                replace(gpu, stable_id="gpd-g1:ffffffffffffffff")
                if gpu.role.value == "external"
                else gpu
                for gpu in attached.snapshot.gpus
            ),
        )
        result = observe_attach_readiness(watch, observed("changed", "sample-c", changed))
        self.assertEqual(result.stage, AttachReadinessStage.ACTION_REQUIRED)
        self.assertEqual(result.code, "attach.identity_changed")

    def test_missing_tv_waits_but_unknown_game_or_session_stops(self):
        watch, attached = self._watch()
        no_tv = replace(
            attached.snapshot,
            displays=tuple(
                replace(display, connected=False, edid_ready=False)
                if display.kind is DisplayKind.EXTERNAL
                else display
                for display in attached.snapshot.displays
            ),
        )
        waiting = observe_attach_readiness(watch, observed("no-tv", "sample-c", no_tv))
        self.assertEqual(waiting.stage, AttachReadinessStage.WAITING_FOR_EXTERNAL_DISPLAY)

        unknown_game = replace(attached.snapshot, game_state=GameState.UNKNOWN)
        result = observe_attach_readiness(
            watch, observed("unknown-game", "sample-d", unknown_game)
        )
        self.assertEqual(result.stage, AttachReadinessStage.ACTION_REQUIRED)
        self.assertEqual(result.code, "attach.game_state_unknown")

    def test_down_or_missing_link_never_appears_ready_idle(self):
        watch, attached = self._watch()
        down = replace(
            attached.snapshot,
            egpu_link=EgpuLinkObservation(
                True, EgpuLinkState.DOWN, Confidence.OBSERVED, "egpu.link_down"
            ),
        )
        result = observe_attach_readiness(watch, observed("down", "sample-c", down))
        self.assertEqual(result.stage, AttachReadinessStage.WAITING_FOR_LINK_HEALTH)
        self.assertEqual(result.code, "attach.link_down")

        unverified = replace(
            attached.snapshot,
            egpu_link=EgpuLinkObservation(False, EgpuLinkState.UNKNOWN, Confidence.UNKNOWN),
        )
        result = observe_attach_readiness(
            watch, observed("unknown-link", "sample-d", unverified)
        )
        self.assertEqual(result.stage, AttachReadinessStage.WAITING_FOR_LINK_HEALTH)
        self.assertEqual(result.code, "attach.link_unverified")

    def test_running_game_never_becomes_idle_transition_ready(self):
        watch, attached = self._watch()
        running = replace(link_up(attached.snapshot), game_state=GameState.RUNNING)

        result = observe_attach_readiness(watch, observed("running", "sample-c", running))

        self.assertEqual(result.stage, AttachReadinessStage.GAME_RUNNING)
        self.assertEqual(result.code, "attach.game_running")

    def test_lifecycle_uses_only_existing_snapshot_updates(self):
        before = observed("portable", "sample-a", snapshot("portable.json"))
        attached = observed("attached", "sample-b", snapshot("connected-internal.json"))
        lifecycle = AttachReadinessLifecycle()

        armed = lifecycle.update(detect_topology_event(before, attached), attached)
        ready = lifecycle.update(
            detect_topology_event(
                attached, observed("attached", "sample-c", link_up(attached.snapshot))
            ),
            observed("attached", "sample-c", link_up(attached.snapshot)),
        )

        self.assertEqual(armed.stage, AttachReadinessStage.SETTLING)
        self.assertEqual(ready.stage, AttachReadinessStage.READY_IDLE)


if __name__ == "__main__":
    unittest.main()
