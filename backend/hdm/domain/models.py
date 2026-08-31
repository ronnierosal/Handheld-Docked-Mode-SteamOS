"""Immutable, I/O-free contracts for observed HDM state."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Confidence(StrEnum):
    UNKNOWN = "unknown"
    OBSERVED = "observed"
    VERIFIED = "verified"


class GpuRole(StrEnum):
    INTERNAL = "internal"
    EXTERNAL = "external"
    UNKNOWN = "unknown"


class DisplayKind(StrEnum):
    INTERNAL = "internal"
    EXTERNAL = "external"
    UNKNOWN = "unknown"


class GameState(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    UNKNOWN = "unknown"


class SupportTier(StrEnum):
    CERTIFIED = "certified"
    COMPATIBLE = "compatible"
    EXPERIMENTAL = "experimental"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"


class OperatingMode(StrEnum):
    PORTABLE = "portable"
    BOOSTED_HANDHELD = "boosted_handheld"
    TV_DOCKED = "tv_docked"
    UNKNOWN = "unknown"
    DEGRADED = "degraded"


class TransitionPhase(StrEnum):
    IDLE = "idle"
    DETECTING = "detecting"
    VALIDATING = "validating"
    PLANNING = "planning"
    PREPARING = "preparing"
    APPLYING = "applying"
    VERIFYING = "verifying"
    COMMITTING = "committing"
    BLOCKED = "blocked"
    ROLLING_BACK = "rolling_back"
    DEGRADED = "degraded"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class Evidence:
    source: str
    confidence: Confidence
    detail: str = ""


@dataclass(frozen=True, slots=True)
class GpuObservation:
    stable_id: str
    role: GpuRole
    vendor_device: str
    present: bool
    selected_for_render: bool | None
    confidence: Confidence
    evidence: tuple[Evidence, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class DisplayObservation:
    stable_id: str
    kind: DisplayKind
    connector: str
    connected: bool | None
    active: bool | None
    edid_ready: bool | None
    confidence: Confidence
    evidence: tuple[Evidence, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class GamescopeObservation:
    running: bool | None
    pid: int | None
    output_order: tuple[str, ...] = field(default_factory=tuple)
    render_gpu_stable_id: str = ""
    render_vendor_device: str = ""
    confidence: Confidence = Confidence.UNKNOWN
    evidence: tuple[Evidence, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class Blocker:
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class ObservedSnapshot:
    schema_version: int
    observed_at: str
    host_profile: str
    support_tier: SupportTier
    game_state: GameState
    gpus: tuple[GpuObservation, ...]
    displays: tuple[DisplayObservation, ...]
    gamescope: GamescopeObservation
    blockers: tuple[Blocker, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class ModeInference:
    mode: OperatingMode
    reasons: tuple[str, ...]
