"""Read-only readiness watch for one exact eGPU-attach event.

An attach candidate never authorizes a transition. This small application
contract simply waits for a later fresh snapshot to determine whether the same
verified eGPU has a usable external display and a known game state. A future
transition owner must still obtain its own fresh binding and consent.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ..domain.event_policy import TopologyEvent
from ..domain.models import Confidence, DisplayKind, GameState
from ..ports.transition import VersionedObservation
from ..profiles.registry import resolve_runtime_profiles
from .topology_event_detection import TopologyDetectionStatus, TopologyEventDetection


class AttachReadinessStage(StrEnum):
    SETTLING = "settling"
    WAITING_FOR_EXTERNAL_DISPLAY = "waiting_for_external_display"
    READY_IDLE = "ready_idle"
    GAME_RUNNING = "game_running"
    ACTION_REQUIRED = "action_required"


@dataclass(frozen=True, slots=True)
class AttachReadinessWatch:
    """Private identity binding created only from an exact attach candidate."""

    egpu_stable_id: str
    attached_generation: str
    attached_sample_id: str


@dataclass(frozen=True, slots=True)
class AttachReadinessStatus:
    stage: AttachReadinessStage
    code: str
    poll_after_ms: int

    def __post_init__(self) -> None:
        if self.poll_after_ms <= 0 or self.poll_after_ms > 30_000:
            raise ValueError("attach readiness polling delay is invalid")


def arm_attach_readiness(
    detection: TopologyEventDetection,
    attached: VersionedObservation,
) -> AttachReadinessWatch | None:
    """Bind an exact candidate to the current private eGPU identity."""
    if (
        detection.status is not TopologyDetectionStatus.DETECTED
        or detection.event is not TopologyEvent.EGPU_ATTACHED
        or detection.current_generation != attached.generation
        or detection.current_sample_id != attached.sample_id
    ):
        return None
    profiles = resolve_runtime_profiles(attached.snapshot)
    if not profiles.exact_host or not profiles.exact_egpu or not profiles.egpu_stable_id:
        return None
    return AttachReadinessWatch(
        profiles.egpu_stable_id,
        attached.generation,
        attached.sample_id,
    )


def observe_attach_readiness(
    watch: AttachReadinessWatch,
    current: VersionedObservation | None,
) -> AttachReadinessStatus:
    """Classify a newer observation without inferring docking permission."""
    if current is None:
        return _status(AttachReadinessStage.ACTION_REQUIRED, "attach.observation_unavailable")
    if current.sample_id == watch.attached_sample_id:
        return _status(AttachReadinessStage.SETTLING, "attach.sample_not_fresh")
    profiles = resolve_runtime_profiles(current.snapshot)
    if (
        not profiles.exact_host
        or not profiles.exact_egpu
        or profiles.egpu_stable_id != watch.egpu_stable_id
    ):
        return _status(AttachReadinessStage.ACTION_REQUIRED, "attach.identity_changed")
    if (
        current.snapshot.gamescope.running is not True
        or current.snapshot.gamescope.confidence is not Confidence.VERIFIED
    ):
        return _status(AttachReadinessStage.ACTION_REQUIRED, "attach.session_unverified")
    if current.snapshot.game_state is GameState.UNKNOWN:
        return _status(AttachReadinessStage.ACTION_REQUIRED, "attach.game_state_unknown")
    external = tuple(
        display
        for display in current.snapshot.displays
        if display.kind is DisplayKind.EXTERNAL
        and display.connected is True
        and display.edid_ready is True
        and display.confidence is Confidence.VERIFIED
    )
    if len(external) != 1:
        return _status(
            AttachReadinessStage.WAITING_FOR_EXTERNAL_DISPLAY,
            "attach.external_display_unready",
        )
    if current.snapshot.game_state is GameState.RUNNING:
        return _status(AttachReadinessStage.GAME_RUNNING, "attach.game_running")
    return _status(AttachReadinessStage.READY_IDLE, "attach.ready_idle")


def _status(stage: AttachReadinessStage, code: str) -> AttachReadinessStatus:
    return AttachReadinessStatus(
        stage,
        code,
        750 if stage is AttachReadinessStage.SETTLING else 1_000,
    )
