"""Deterministic fake-signal and mandatory re-scan process-release runner."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import re

from .process_release import (
    revalidate_process_release,
    revalidate_process_release_rescan,
    revalidate_process_release_target,
)
from ..domain.models import EgpuResourceKind
from ..domain.process_release import (
    ProcessReleaseApproval,
    ReleasePhase,
)
from ..ports.process_signal import (
    ProcessSignalAction,
    ProcessSignalPort,
)
from ..ports.transition import (
    MonotonicClockPort,
    TransitionObservationPort,
    VersionedObservation,
)


MAX_PROCESS_AUDIT_EVENTS = 96


class ProcessReleaseStatus(StrEnum):
    COMPLETED = "completed"
    BLOCKED = "blocked"
    ACTION_REQUIRED = "action_required"


@dataclass(frozen=True, slots=True)
class ProcessReleaseAuditEvent:
    sequence: int
    phase: ReleasePhase
    code: str
    target_index: int | None = None
    resources: tuple[EgpuResourceKind, ...] = field(default_factory=tuple)
    outcome: str = ""

    def __post_init__(self) -> None:
        if self.sequence <= 0:
            raise ValueError("process audit sequence must be positive")
        if not re.fullmatch(r"[a-z0-9_.-]{1,64}", self.code):
            raise ValueError("process audit code must be categorical")
        if self.target_index is not None and self.target_index <= 0:
            raise ValueError("process audit target index must be positive")
        if self.outcome and not re.fullmatch(r"[a-z0-9_.-]{1,64}", self.outcome):
            raise ValueError("process audit outcome must be categorical")


@dataclass(frozen=True, slots=True)
class ProcessTargetResult:
    target_index: int
    signal_requested: bool
    released: bool
    code: str


@dataclass(frozen=True, slots=True)
class ProcessReleaseReplayResult:
    status: ProcessReleaseStatus
    software_blockers_cleared: bool
    hardware_removal_authorized: bool
    target_results: tuple[ProcessTargetResult, ...]
    remaining_client_count: int | None
    audit: tuple[ProcessReleaseAuditEvent, ...]
    reason_code: str = ""


def process_audit_to_dict(
    events: tuple[ProcessReleaseAuditEvent, ...]
) -> list[dict[str, object]]:
    return [
        {
            "sequence": event.sequence,
            "phase": event.phase.value,
            "code": event.code,
            "target_index": event.target_index,
            "resources": [resource.value for resource in event.resources],
            "outcome": event.outcome,
        }
        for event in events
    ]


class ProcessReleaseReplaySimulator:
    def __init__(
        self,
        observations: TransitionObservationPort,
        signals: ProcessSignalPort,
        clock: MonotonicClockPort,
        *,
        per_signal_deadline_ms: int = 2_000,
    ) -> None:
        if per_signal_deadline_ms <= 0 or per_signal_deadline_ms > 10_000:
            raise ValueError("process signal deadline must be between 1 and 10000 ms")
        self._observations = observations
        self._signals = signals
        self._clock = clock
        self._deadline_ms = per_signal_deadline_ms

    def run(
        self,
        approval: ProcessReleaseApproval,
        current: VersionedObservation,
    ) -> ProcessReleaseReplayResult:
        audit: list[ProcessReleaseAuditEvent] = []
        results: list[ProcessTargetResult] = []

        def record(
            code: str,
            *,
            target_index: int | None = None,
            resources: tuple[EgpuResourceKind, ...] = (),
            outcome: str = "",
        ) -> None:
            if len(audit) >= MAX_PROCESS_AUDIT_EVENTS:
                raise ValueError("process release audit exceeded its bound")
            audit.append(
                ProcessReleaseAuditEvent(
                    len(audit) + 1,
                    approval.phase,
                    code,
                    target_index,
                    resources,
                    outcome,
                )
            )

        try:
            revalidate_process_release(
                approval,
                current.snapshot,
                observed_generation=current.generation,
            )
        except ValueError:
            record("approval.revalidation_failed", outcome="blocked")
            return self._result(
                ProcessReleaseStatus.BLOCKED,
                False,
                results,
                current,
                audit,
                "approval.revalidation_failed",
            )
        record("approval.revalidated", outcome="verified")
        previous_generation = approval.observed_generation

        for index, target in enumerate(approval.targets, start=1):
            try:
                live_target = revalidate_process_release_target(
                    approval,
                    current.snapshot,
                    observed_generation=current.generation,
                    previous_generation=previous_generation,
                    target=target,
                )
            except ValueError:
                record(
                    "target.revalidation_failed",
                    target_index=index,
                    resources=target.resources,
                    outcome="blocked",
                )
                return self._result(
                    ProcessReleaseStatus.BLOCKED,
                    False,
                    results,
                    current,
                    audit,
                    "target.revalidation_failed",
                )
            if live_target is None:
                results.append(
                    ProcessTargetResult(index, False, True, "target.already_released")
                )
                record(
                    "target.already_released",
                    target_index=index,
                    resources=target.resources,
                    outcome="no_op",
                )
                continue

            action = (
                ProcessSignalAction.GRACEFUL_TERMINATE
                if approval.phase is ReleasePhase.GRACEFUL
                else ProcessSignalAction.FORCE_TERMINATE
            )
            record(
                "target.signal_requested",
                target_index=index,
                resources=target.resources,
                outcome=action.value,
            )
            started = self._clock.now_ms()
            signal_result = self._signals.signal(live_target, action)
            elapsed = self._clock.now_ms() - started
            signal_generation = current.generation
            rescanned = self._observations.observe()
            if rescanned is None:
                record(
                    "target.rescan_unavailable",
                    target_index=index,
                    resources=target.resources,
                    outcome="action_required",
                )
                results.append(
                    ProcessTargetResult(index, True, False, "rescan.unavailable")
                )
                return self._result(
                    ProcessReleaseStatus.ACTION_REQUIRED,
                    False,
                    results,
                    None,
                    audit,
                    "rescan.unavailable",
                )
            current = rescanned
            previous_generation = signal_generation
            try:
                revalidate_process_release_rescan(
                    approval,
                    current.snapshot,
                    observed_generation=current.generation,
                    previous_generation=signal_generation,
                )
            except ValueError:
                record(
                    "target.rescan_invalid",
                    target_index=index,
                    resources=target.resources,
                    outcome="action_required",
                )
                results.append(
                    ProcessTargetResult(index, True, False, "rescan.invalid")
                )
                return self._result(
                    ProcessReleaseStatus.ACTION_REQUIRED,
                    False,
                    results,
                    current,
                    audit,
                    "rescan.invalid",
                )
            target_present = any(
                client.instance_id == target.instance_id
                for client in current.snapshot.disconnect_readiness.clients
            )
            released = not target_present
            code = "target.released" if released else "target.remaining"
            results.append(ProcessTargetResult(index, True, released, code))
            record(
                "target.rescanned",
                target_index=index,
                resources=target.resources,
                outcome="released" if released else "remaining",
            )
            if elapsed < 0 or elapsed > self._deadline_ms:
                return self._result(
                    ProcessReleaseStatus.ACTION_REQUIRED,
                    False,
                    results,
                    current,
                    audit,
                    "signal.deadline_exceeded",
                )
            if not signal_result.accepted:
                return self._result(
                    ProcessReleaseStatus.ACTION_REQUIRED,
                    False,
                    results,
                    current,
                    audit,
                    signal_result.code,
                )

        readiness = current.snapshot.disconnect_readiness
        software_ready = bool(
            readiness.applicable
            and readiness.scan_complete
            and readiness.ready
            and not readiness.clients
            and not readiness.storage_in_use
        )
        record(
            "release.final_readiness",
            outcome="cleared" if software_ready else "blocked",
        )
        return self._result(
            ProcessReleaseStatus.COMPLETED,
            software_ready,
            results,
            current,
            audit,
            "" if software_ready else "software_blockers_remain",
        )

    @staticmethod
    def _result(
        status: ProcessReleaseStatus,
        software_ready: bool,
        results: list[ProcessTargetResult],
        current: VersionedObservation | None,
        audit: list[ProcessReleaseAuditEvent],
        reason_code: str,
    ) -> ProcessReleaseReplayResult:
        remaining = (
            len(current.snapshot.disconnect_readiness.clients)
            if current is not None
            else None
        )
        return ProcessReleaseReplayResult(
            status=status,
            software_blockers_cleared=software_ready,
            hardware_removal_authorized=False,
            target_results=tuple(results),
            remaining_client_count=remaining,
            audit=tuple(audit),
            reason_code=reason_code,
        )
