"""Narrow boundaries used by the deterministic transition replay engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..domain.control_plane import PlannedStep, TransitionPlan
from ..domain.models import ObservedSnapshot


@dataclass(frozen=True, slots=True)
class VersionedObservation:
    generation: str
    snapshot: ObservedSnapshot


@dataclass(frozen=True, slots=True)
class MechanismResult:
    succeeded: bool
    code: str


class MonotonicClockPort(Protocol):
    def now_ms(self) -> int:
        """Return a monotonic millisecond value."""


class TransitionObservationPort(Protocol):
    def observe(self) -> VersionedObservation | None:
        """Return the next complete observation, or None when unavailable."""


class TransitionMechanismPort(Protocol):
    def apply(self, step: PlannedStep) -> MechanismResult:
        """Apply one typed step. Production adapters do not exist yet."""

    def recover(self, plan: TransitionPlan) -> MechanismResult:
        """Attempt bounded restoration of the plan's known-good placement."""

