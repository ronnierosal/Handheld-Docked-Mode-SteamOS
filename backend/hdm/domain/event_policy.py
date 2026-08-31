"""Pure fail-closed policy for asynchronous topology and input events."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .control_plane import PlacementState, WorkflowState


class TopologyEvent(StrEnum):
    EGPU_ATTACHED = "egpu_attached"
    EGPU_REMOVED = "egpu_removed"
    EXTERNAL_DISPLAY_LOST = "external_display_lost"
    EXTERNAL_CONTROLLER_LOST = "external_controller_lost"
    TIMEOUT = "timeout"


class RecoveryDirective(StrEnum):
    OBSERVE_STABILITY = "observe_stability"
    RECOVER_PORTABLE = "recover_portable"
    CONTINUE_PENDING_SLEEP_AFTER_RECOVERY = "continue_pending_sleep_after_recovery"
    RESTORE_BUILTIN_CONTROLLER = "restore_builtin_controller"
    ACTION_REQUIRED = "action_required"


@dataclass(frozen=True, slots=True)
class EventDecision:
    directives: tuple[RecoveryDirective, ...]
    next_workflow: WorkflowState
    reason_code: str


def decide_topology_event(
    *,
    event: TopologyEvent,
    placement: PlacementState,
    workflow: WorkflowState,
    builtin_controller_available: bool | None = None,
) -> EventDecision:
    if event is TopologyEvent.EGPU_ATTACHED:
        return EventDecision(
            (RecoveryDirective.OBSERVE_STABILITY,),
            WorkflowState.CONNECTING,
            "egpu.attached_observe",
        )

    if event is TopologyEvent.EGPU_REMOVED:
        directives = [RecoveryDirective.RECOVER_PORTABLE]
        if workflow is WorkflowState.SLEEP_PENDING_DISCONNECT:
            directives.append(RecoveryDirective.CONTINUE_PENDING_SLEEP_AFTER_RECOVERY)
        return EventDecision(
            tuple(directives),
            WorkflowState.RETURNING_TO_PORTABLE,
            "egpu.removed_recover",
        )

    if event is TopologyEvent.EXTERNAL_CONTROLLER_LOST:
        if builtin_controller_available is True:
            return EventDecision(
                (RecoveryDirective.RESTORE_BUILTIN_CONTROLLER,),
                workflow,
                "controller.restore_builtin",
            )
        return EventDecision(
            (RecoveryDirective.ACTION_REQUIRED,),
            WorkflowState.ACTION_REQUIRED,
            "controller.fallback_unknown",
        )

    if event is TopologyEvent.EXTERNAL_DISPLAY_LOST and placement in (
        PlacementState.DOCKED_IGPU,
        PlacementState.DOCKED_EGPU,
    ):
        return EventDecision(
            (RecoveryDirective.RECOVER_PORTABLE,),
            WorkflowState.RETURNING_TO_PORTABLE,
            "display.external_lost",
        )

    return EventDecision(
        (RecoveryDirective.ACTION_REQUIRED,),
        WorkflowState.ACTION_REQUIRED,
        "event.state_unverified",
    )

