from __future__ import annotations

import dataclasses
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from hdm.application.process_release import (  # noqa: E402
    GracefulReleaseEvidence,
    ProcessReleaseApprovalStore,
)
from hdm.application.process_release_replay import (  # noqa: E402
    ProcessReleaseReplaySimulator,
    ProcessReleaseStatus,
    process_audit_to_dict,
)
from hdm.domain.models import (  # noqa: E402
    EgpuClientKind,
    EgpuClientObservation,
    EgpuResourceKind,
)
from hdm.domain.serialization import snapshot_from_dict  # noqa: E402
from hdm.domain.process_release import ReleasePhase  # noqa: E402
from hdm.ports.process_signal import (  # noqa: E402
    ProcessSignalAction,
    ProcessSignalResult,
)
from hdm.ports.transition import VersionedObservation  # noqa: E402


FIXTURES = ROOT / "tests" / "fixtures"


def base_snapshot():
    value = json.loads((FIXTURES / "portable.json").read_text(encoding="utf-8"))
    value["disconnect_readiness"] = {
        "applicable": True,
        "scan_complete": True,
        "ready": False,
        "egpu_stable_id": "gpd-g1:ephemeral",
        "clients": [],
        "storage_devices": 0,
        "storage_in_use": False,
        "error": "",
    }
    return snapshot_from_dict(value)


def client(instance_id: str, pid: int) -> EgpuClientObservation:
    return EgpuClientObservation(
        instance_id=instance_id,
        pid=pid,
        name="test-client",
        kind=EgpuClientKind.USER,
        resources=(EgpuResourceKind.DRM_RENDER,),
        close_eligible=True,
        reason="test fixture",
    )


def with_clients(snapshot, *clients, complete=True):
    readiness = dataclasses.replace(
        snapshot.disconnect_readiness,
        clients=tuple(clients),
        scan_complete=complete,
        ready=complete and not clients,
    )
    return dataclasses.replace(snapshot, disconnect_readiness=readiness)


class FakeClock:
    def __init__(self) -> None:
        self.value = 0

    def now_ms(self) -> int:
        return self.value

    def advance(self, milliseconds: int) -> None:
        self.value += milliseconds


class Observations:
    def __init__(self, *values):
        self.values = list(values)

    def observe(self):
        return self.values.pop(0) if self.values else None


class Signals:
    def __init__(self, clock, *results):
        self.clock = clock
        self.results = list(results)
        self.calls = []

    def signal(self, target, action):
        self.calls.append((target, action))
        duration, result = self.results.pop(0)
        self.clock.advance(duration)
        return result


def approval(snapshot, phase=ReleasePhase.GRACEFUL):
    tokens = iter(["approval_token_123456"])
    store = ProcessReleaseApprovalStore(
        token_factory=lambda: next(tokens), monotonic=lambda: 0.0
    )
    kwargs = {}
    generation = "generation-1"
    if phase is ReleasePhase.FORCE:
        kwargs["graceful_evidence"] = GracefulReleaseEvidence(
            "graceful_operation_1",
            tuple(client.instance_id for client in snapshot.disconnect_readiness.clients),
            "generation-0",
        )
    preview = store.issue(
        snapshot,
        observed_generation=generation,
        phase=phase,
        **kwargs,
    )
    return store.consume(preview.token)


class ProcessReleaseReplayTests(unittest.TestCase):
    def test_rescans_after_every_fake_signal_and_clears_software_blockers(self):
        first = client("instance-1", 100)
        second = client("instance-2", 200)
        initial = with_clients(base_snapshot(), first, second)
        after_first = with_clients(initial, second)
        after_second = with_clients(initial)
        clock = FakeClock()
        signals = Signals(
            clock,
            (10, ProcessSignalResult(True, "signal.accepted")),
            (10, ProcessSignalResult(True, "signal.accepted")),
        )
        result = ProcessReleaseReplaySimulator(
            Observations(
                VersionedObservation("generation-3", after_first),
                VersionedObservation("generation-4", after_second),
            ),
            signals,
            clock,
        ).run(
            approval(initial),
            VersionedObservation("generation-2", initial),
        )
        self.assertEqual(result.status, ProcessReleaseStatus.COMPLETED)
        self.assertTrue(result.software_blockers_cleared)
        self.assertFalse(result.hardware_removal_authorized)
        self.assertEqual(len(signals.calls), 2)
        self.assertTrue(all(item.released for item in result.target_results))

    def test_remaining_process_is_reported_without_force_escalation(self):
        target = client("instance-1", 100)
        initial = with_clients(base_snapshot(), target)
        clock = FakeClock()
        signals = Signals(clock, (10, ProcessSignalResult(True, "signal.accepted")))
        result = ProcessReleaseReplaySimulator(
            Observations(VersionedObservation("generation-3", initial)),
            signals,
            clock,
        ).run(approval(initial), VersionedObservation("generation-2", initial))
        self.assertEqual(result.status, ProcessReleaseStatus.COMPLETED)
        self.assertFalse(result.software_blockers_cleared)
        self.assertEqual(result.reason_code, "software_blockers_remain")
        self.assertEqual(signals.calls[0][1], ProcessSignalAction.GRACEFUL_TERMINATE)

    def test_changed_client_set_stops_before_next_signal(self):
        first = client("instance-1", 100)
        second = client("instance-2", 200)
        unexpected = client("unexpected-3", 300)
        initial = with_clients(base_snapshot(), first, second)
        changed = with_clients(initial, second, unexpected)
        clock = FakeClock()
        signals = Signals(clock, (10, ProcessSignalResult(True, "signal.accepted")))
        result = ProcessReleaseReplaySimulator(
            Observations(VersionedObservation("generation-3", changed)),
            signals,
            clock,
        ).run(approval(initial), VersionedObservation("generation-2", initial))
        self.assertEqual(result.status, ProcessReleaseStatus.ACTION_REQUIRED)
        self.assertEqual(len(signals.calls), 1)
        self.assertEqual(result.reason_code, "rescan.invalid")

    def test_stale_or_incomplete_post_signal_scan_requires_action(self):
        target = client("instance-1", 100)
        initial = with_clients(base_snapshot(), target)
        cases = (
            VersionedObservation("generation-2", with_clients(initial)),
            VersionedObservation(
                "generation-3", with_clients(initial, complete=False)
            ),
        )
        for observed in cases:
            with self.subTest(generation=observed.generation):
                clock = FakeClock()
                signals = Signals(
                    clock, (10, ProcessSignalResult(True, "signal.accepted"))
                )
                result = ProcessReleaseReplaySimulator(
                    Observations(observed), signals, clock
                ).run(
                    approval(initial),
                    VersionedObservation("generation-2", initial),
                )
                self.assertEqual(result.status, ProcessReleaseStatus.ACTION_REQUIRED)
                self.assertEqual(result.reason_code, "rescan.invalid")

    def test_missing_rescan_and_deadline_expiry_require_action(self):
        target = client("instance-1", 100)
        initial = with_clients(base_snapshot(), target)
        for observations, duration, reason in (
            (Observations(None), 10, "rescan.unavailable"),
            (
                Observations(
                    VersionedObservation(
                        "generation-3", with_clients(initial)
                    )
                ),
                201,
                "signal.deadline_exceeded",
            ),
        ):
            with self.subTest(reason=reason):
                clock = FakeClock()
                signals = Signals(
                    clock, (duration, ProcessSignalResult(True, "signal.accepted"))
                )
                result = ProcessReleaseReplaySimulator(
                    observations, signals, clock, per_signal_deadline_ms=200
                ).run(
                    approval(initial),
                    VersionedObservation("generation-2", initial),
                )
                self.assertEqual(result.status, ProcessReleaseStatus.ACTION_REQUIRED)
                self.assertEqual(result.reason_code, reason)

    def test_force_approval_uses_force_action_and_audit_has_no_identity(self):
        target = client("private-instance-token", 4242)
        initial = with_clients(base_snapshot(), target)
        clock = FakeClock()
        signals = Signals(clock, (10, ProcessSignalResult(True, "signal.accepted")))
        result = ProcessReleaseReplaySimulator(
            Observations(
                VersionedObservation("generation-3", with_clients(initial))
            ),
            signals,
            clock,
        ).run(
            approval(initial, ReleasePhase.FORCE),
            VersionedObservation("generation-2", initial),
        )
        self.assertEqual(signals.calls[0][1], ProcessSignalAction.FORCE_TERMINATE)
        exported = json.dumps(process_audit_to_dict(result.audit), sort_keys=True)
        self.assertNotIn("4242", exported)
        self.assertNotIn("private-instance-token", exported)
        self.assertNotIn("test-client", exported)
        self.assertNotIn("pid", exported.casefold())


if __name__ == "__main__":
    unittest.main()
