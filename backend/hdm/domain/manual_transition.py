"""Pure fail-closed planning for one future manual presentation transition."""

from __future__ import annotations

from dataclasses import dataclass

from .control_plane import (
    CapabilitySupport,
    EffectiveCapabilities,
    PlacementState,
    PlannedStep,
    TransitionPlan,
    WorkflowState,
)
from .models import GameState


@dataclass(frozen=True, slots=True)
class ManualTransitionEvidence:
    observed_generation: str
    exact_host_identity_verified: bool
    exact_egpu_identity_verified: bool
    external_display_ready_verified: bool
    egpu_render_ready_verified: bool
    internal_display_ready_verified: bool
    source_recovery_ready_verified: bool
    game_state: GameState

    def __post_init__(self) -> None:
        if not self.observed_generation:
            raise ValueError("manual transition generation is required")


@dataclass(frozen=True, slots=True)
class ManualPlanDecision:
    plan: TransitionPlan | None
    blockers: tuple[str, ...]

    def __post_init__(self) -> None:
        if (self.plan is None) == (not self.blockers):
            raise ValueError("manual plan decision requires either a plan or blockers")


def plan_manual_transition(
    *,
    plan_id: str,
    request_id: str,
    current: PlacementState,
    target: PlacementState,
    capabilities: EffectiveCapabilities,
    evidence: ManualTransitionEvidence,
    step_deadline_ms: int = 15_000,
    recovery_deadline_ms: int = 15_000,
) -> ManualPlanDecision:
    if step_deadline_ms <= 0 or recovery_deadline_ms <= 0:
        raise ValueError("manual transition deadlines must be positive")
    blockers: list[str] = []
    if current in {PlacementState.UNKNOWN, PlacementState.DEGRADED}:
        blockers.append("placement.current_unverified")
    if target not in {PlacementState.PORTABLE, PlacementState.DOCKED_EGPU}:
        blockers.append("placement.target_unsupported")
    if current not in {PlacementState.PORTABLE, PlacementState.DOCKED_EGPU}:
        blockers.append("placement.path_unsupported")
    if not evidence.exact_host_identity_verified:
        blockers.append("identity.host_unverified")
    if blockers:
        return ManualPlanDecision(None, tuple(blockers))

    workflow = (
        WorkflowState.CONNECTING
        if target is PlacementState.DOCKED_EGPU
        else WorkflowState.RETURNING_TO_PORTABLE
    )
    if current is target:
        return ManualPlanDecision(
            TransitionPlan(
                plan_id=plan_id,
                request_id=request_id,
                observed_generation=evidence.observed_generation,
                from_placement=current,
                target_placement=target,
                workflow_state=workflow,
                recovery_deadline_ms=recovery_deadline_ms,
            ),
            (),
        )

    if capabilities.display_handoff is not CapabilitySupport.VERIFIED:
        blockers.append("capability.display_handoff_unverified")
    if evidence.game_state is GameState.UNKNOWN:
        blockers.append("game.state_unknown")
    elif evidence.game_state is GameState.RUNNING:
        blockers.append("game.running")
    if not evidence.source_recovery_ready_verified:
        blockers.append("recovery.source_unverified")

    if target is PlacementState.DOCKED_EGPU:
        if not evidence.exact_egpu_identity_verified:
            blockers.append("identity.egpu_unverified")
        if not evidence.external_display_ready_verified:
            blockers.append("display.external_unready")
        if not evidence.egpu_render_ready_verified:
            blockers.append("render.egpu_unready")
        step_code = "presentation.apply_docked_egpu"
    else:
        if not evidence.internal_display_ready_verified:
            blockers.append("display.internal_unready")
        step_code = "presentation.restore_portable"

    if blockers:
        return ManualPlanDecision(None, tuple(blockers))
    return ManualPlanDecision(
        TransitionPlan(
            plan_id=plan_id,
            request_id=request_id,
            observed_generation=evidence.observed_generation,
            from_placement=current,
            target_placement=target,
            workflow_state=workflow,
            steps=(
                PlannedStep(
                    step_code,
                    step_deadline_ms,
                    expected_placement=target,
                ),
            ),
            recovery_deadline_ms=recovery_deadline_ms,
        ),
        (),
    )
