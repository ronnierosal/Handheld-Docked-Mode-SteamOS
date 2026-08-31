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
    revalidate_process_release,
)
from hdm.domain.models import (  # noqa: E402
    EgpuClientKind,
    EgpuClientObservation,
    EgpuResourceKind,
)
from hdm.domain.serialization import snapshot_from_dict  # noqa: E402
from hdm.domain.process_release import ReleasePhase  # noqa: E402


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


def client(
    *,
    instance_id: str = "instance-1",
    pid: int = 100,
    kind: EgpuClientKind = EgpuClientKind.USER,
    close_eligible: bool = True,
    resources: tuple[EgpuResourceKind, ...] = (EgpuResourceKind.DRM_RENDER,),
) -> EgpuClientObservation:
    return EgpuClientObservation(
        instance_id=instance_id,
        pid=pid,
        name="test-client",
        kind=kind,
        resources=resources,
        close_eligible=close_eligible,
        reason="test fixture",
    )


def with_clients(snapshot, *clients, storage_in_use=False):
    readiness = dataclasses.replace(
        snapshot.disconnect_readiness,
        clients=tuple(clients),
        storage_in_use=storage_in_use,
        ready=False,
    )
    return dataclasses.replace(snapshot, disconnect_readiness=readiness)


class FakeTime:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value


class ProcessReleaseApprovalTests(unittest.TestCase):
    def store(self, clock=None, tokens=None):
        token_values = iter(tokens or ["approval_token_123456"])
        return ProcessReleaseApprovalStore(
            ttl_seconds=10,
            monotonic=clock or (lambda: 0.0),
            token_factory=lambda: next(token_values),
        )

    def test_preview_targets_only_close_eligible_user_processes(self):
        snapshot = with_clients(
            base_snapshot(),
            client(),
            client(
                instance_id="protected-1",
                pid=200,
                kind=EgpuClientKind.PROTECTED,
                close_eligible=False,
            ),
        )
        preview = self.store().issue(
            snapshot,
            observed_generation="generation-1",
            phase=ReleasePhase.GRACEFUL,
        )
        self.assertEqual(len(preview.targets), 1)
        self.assertEqual(preview.protected_client_count, 1)
        self.assertFalse(hasattr(preview.targets[0], "pid"))
        self.assertFalse(hasattr(preview.targets[0], "instance_id"))

    def test_token_is_single_use_expires_and_binds_phase(self):
        clock = FakeTime()
        store = self.store(clock)
        snapshot = with_clients(base_snapshot(), client())
        graceful_evidence = GracefulReleaseEvidence(
            operation_id="graceful_operation_1",
            attempted_instance_ids=("instance-1",),
            observed_generation="generation-1",
        )
        preview = store.issue(
            snapshot,
            observed_generation="generation-2",
            phase=ReleasePhase.FORCE,
            graceful_evidence=graceful_evidence,
        )
        approval = store.consume(preview.token)
        self.assertEqual(approval.phase, ReleasePhase.FORCE)
        self.assertEqual(
            approval.prior_graceful_operation_id, "graceful_operation_1"
        )
        with self.assertRaisesRegex(ValueError, "already used"):
            store.consume(preview.token)

        store = self.store(clock, ["approval_token_654321"])
        preview = store.issue(
            snapshot,
            observed_generation="generation-1",
            phase=ReleasePhase.GRACEFUL,
        )
        clock.value = 11
        with self.assertRaisesRegex(ValueError, "expired"):
            store.consume(preview.token)

    def test_force_approval_requires_prior_attempt_and_cannot_add_targets(self):
        snapshot = with_clients(base_snapshot(), client())
        with self.assertRaisesRegex(ValueError, "prior graceful"):
            self.store().issue(
                snapshot,
                observed_generation="generation-2",
                phase=ReleasePhase.FORCE,
            )
        evidence = GracefulReleaseEvidence(
            operation_id="graceful_operation_1",
            attempted_instance_ids=("different-instance",),
            observed_generation="generation-1",
        )
        with self.assertRaisesRegex(ValueError, "new process target"):
            self.store().issue(
                snapshot,
                observed_generation="generation-2",
                phase=ReleasePhase.FORCE,
                graceful_evidence=evidence,
            )

    def test_revalidation_requires_fresh_identical_evidence(self):
        snapshot = with_clients(base_snapshot(), client())
        store = self.store()
        preview = store.issue(
            snapshot,
            observed_generation="generation-1",
            phase=ReleasePhase.GRACEFUL,
        )
        approval = store.consume(preview.token)
        with self.assertRaisesRegex(ValueError, "fresh observation"):
            revalidate_process_release(
                approval, snapshot, observed_generation="generation-1"
            )
        targets = revalidate_process_release(
            approval, snapshot, observed_generation="generation-2"
        )
        self.assertEqual(targets[0].pid, 100)

    def test_pid_reuse_resource_change_and_egpu_change_fail_closed(self):
        snapshot = with_clients(base_snapshot(), client())
        store = self.store()
        approval = store.consume(
            store.issue(
                snapshot,
                observed_generation="generation-1",
                phase=ReleasePhase.GRACEFUL,
            ).token
        )
        cases = (
            with_clients(snapshot, client(instance_id="instance-reused", pid=100)),
            with_clients(
                snapshot,
                client(resources=(EgpuResourceKind.AUDIO_CONTROL,)),
            ),
            dataclasses.replace(
                snapshot,
                disconnect_readiness=dataclasses.replace(
                    snapshot.disconnect_readiness,
                    egpu_stable_id="gpd-g1:different",
                ),
            ),
        )
        for changed in cases:
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                revalidate_process_release(
                    approval, changed, observed_generation="generation-2"
                )

    def test_storage_and_no_eligible_targets_never_issue_approval(self):
        store = self.store()
        protected = client(
            kind=EgpuClientKind.PROTECTED,
            close_eligible=False,
        )
        with self.assertRaisesRegex(ValueError, "no close-eligible"):
            store.issue(
                with_clients(base_snapshot(), protected),
                observed_generation="generation-1",
                phase=ReleasePhase.GRACEFUL,
            )
        with self.assertRaisesRegex(ValueError, "storage"):
            store.issue(
                with_clients(base_snapshot(), client(), storage_in_use=True),
                observed_generation="generation-1",
                phase=ReleasePhase.GRACEFUL,
            )


if __name__ == "__main__":
    unittest.main()
