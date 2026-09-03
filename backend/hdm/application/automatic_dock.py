"""Pure one-shot policy for automatic TV docking after exact attach readiness."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ..domain.control_plane import PlacementState
from ..ports.transition import VersionedObservation
from ..profiles.registry import resolve_runtime_profiles
from .attach_readiness import AttachReadinessStage, AttachReadinessStatus
from ..domain.inference import infer_placement


class AutomaticDockStage(StrEnum):
    DISABLED = "disabled"
    OBSERVING = "observing"
    SETTLING = "settling"
    WAITING = "waiting"
    SWITCHING = "switching"
    DOCKED = "docked"
    ACTION_REQUIRED = "action_required"


@dataclass(frozen=True, slots=True)
class AutomaticDockStatus:
    stage: AutomaticDockStage
    code: str
    enabled: bool


@dataclass(frozen=True, slots=True)
class AutomaticDockDecision:
    status: AutomaticDockStatus
    expected_generation: str = ""

    @property
    def should_switch(self) -> bool:
        return bool(self.expected_generation)


class AutomaticDockCoordinator:
    """Issue at most one request while one exact eGPU remains attached."""

    def __init__(self) -> None:
        self._attempted = False
        self._status = AutomaticDockStatus(
            AutomaticDockStage.DISABLED, "automatic_dock.disabled", False
        )

    def status(self) -> AutomaticDockStatus:
        return self._status

    def update(
        self,
        *,
        enabled: bool,
        readiness: AttachReadinessStatus,
        current: VersionedObservation,
    ) -> AutomaticDockDecision:
        profiles = resolve_runtime_profiles(current.snapshot)
        if not profiles.exact_egpu:
            self._attempted = False
        if not enabled:
            self._attempted = False
            self._status = AutomaticDockStatus(
                AutomaticDockStage.DISABLED, "automatic_dock.disabled", False
            )
            return AutomaticDockDecision(self._status)
        if not profiles.exact_host or not profiles.exact_egpu:
            self._status = AutomaticDockStatus(
                AutomaticDockStage.OBSERVING,
                "automatic_dock.waiting_for_exact_g1",
                True,
            )
            return AutomaticDockDecision(self._status)
        placement = infer_placement(current.snapshot)
        if placement is PlacementState.DOCKED_EGPU:
            self._attempted = True
            self._status = AutomaticDockStatus(
                AutomaticDockStage.DOCKED, "automatic_dock.tv_active", True
            )
            return AutomaticDockDecision(self._status)
        if self._attempted:
            return AutomaticDockDecision(self._status)
        if readiness.stage is AttachReadinessStage.READY_IDLE:
            if placement is not PlacementState.PORTABLE:
                self._status = AutomaticDockStatus(
                    AutomaticDockStage.ACTION_REQUIRED,
                    "automatic_dock.source_unverified",
                    True,
                )
                return AutomaticDockDecision(self._status)
            self._attempted = True
            self._status = AutomaticDockStatus(
                AutomaticDockStage.SWITCHING, "automatic_dock.switch_requested", True
            )
            return AutomaticDockDecision(self._status, current.generation)
        if readiness.stage is AttachReadinessStage.SETTLING:
            stage = AutomaticDockStage.SETTLING
        elif readiness.stage is AttachReadinessStage.ACTION_REQUIRED:
            stage = AutomaticDockStage.ACTION_REQUIRED
        else:
            stage = AutomaticDockStage.WAITING
        self._status = AutomaticDockStatus(stage, readiness.code, True)
        return AutomaticDockDecision(self._status)

    def reset_after_acknowledgement(self) -> AutomaticDockStatus:
        """Permit one fresh re-evaluation after the player clears a journal."""
        self._attempted = False
        self._status = AutomaticDockStatus(
            AutomaticDockStage.OBSERVING,
            "automatic_dock.rearmed_after_acknowledgement",
            True,
        )
        return self._status

    def record_result(self, code: str, *, succeeded: bool) -> AutomaticDockStatus:
        self._status = AutomaticDockStatus(
            AutomaticDockStage.DOCKED if succeeded else AutomaticDockStage.ACTION_REQUIRED,
            code,
            True,
        )
        return self._status
