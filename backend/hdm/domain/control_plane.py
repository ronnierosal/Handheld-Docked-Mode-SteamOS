"""Pure typed contracts for future HDM transitions and capabilities.

These contracts do not authorize or perform a mutation.  They keep observed
placement, request progress, and hardware capability evidence independent so a
workflow cannot overwrite current hardware truth.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class PlacementState(StrEnum):
    PORTABLE = "portable"
    BOOSTED_HANDHELD = "boosted_handheld"
    DOCKED_IGPU = "docked_igpu"
    DOCKED_EGPU = "docked_egpu"
    UNKNOWN = "unknown"
    DEGRADED = "degraded"


class WorkflowState(StrEnum):
    IDLE = "idle"
    CONNECTING = "connecting"
    PREPARING_TO_DISCONNECT = "preparing_to_disconnect"
    SAFE_TO_DISCONNECT = "safe_to_disconnect"
    RETURNING_TO_PORTABLE = "returning_to_portable"
    SLEEP_PENDING_DISCONNECT = "sleep_pending_disconnect"
    ACTION_REQUIRED = "action_required"
    RECOVERING = "recovering"
    FAILED = "failed"


class RequestIntent(StrEnum):
    DOCK = "dock"
    UNDOCK = "undock"
    SLEEP = "sleep"
    RECOVER = "recover"


class RequestSource(StrEnum):
    MANUAL = "manual"
    AUTOMATIC = "automatic"
    STEAM_MENU = "steam_menu"
    PHYSICAL_BUTTON = "physical_button"


class CapabilitySupport(StrEnum):
    UNKNOWN = "unknown"
    UNSUPPORTED = "unsupported"
    EXPERIMENTAL = "experimental"
    VERIFIED = "verified"


class EgpuTransport(StrEnum):
    NONE = "none"
    USB4 = "usb4"
    USB5 = "usb5"
    OCULINK = "oculink"
    UNKNOWN = "unknown"


class SleepBehavior(StrEnum):
    UNTESTED = "untested"
    SLEEP_SAFE_VERIFIED = "sleep_safe_verified"
    DISCONNECT_BEFORE_SLEEP_VERIFIED = "disconnect_before_sleep_verified"
    SLEEP_UNRELIABLE = "sleep_unreliable"
    KNOWN_ISSUE = "known_issue"


class RemovalBehavior(StrEnum):
    UNKNOWN = "unknown"
    UNTESTED = "untested"
    LIVE_REMOVAL_VERIFIED = "live_removal_verified"
    SHUTDOWN_BEFORE_DISCONNECT = "shutdown_before_disconnect"
    KNOWN_ISSUE = "known_issue"


class TransitionOutcomeKind(StrEnum):
    SUCCEEDED = "succeeded"
    NO_OP = "no_op"
    BLOCKED = "blocked"
    RECOVERED = "recovered"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class HostCapabilities:
    profile_id: str
    egpu_support: CapabilitySupport = CapabilitySupport.UNKNOWN
    egpu_transport: EgpuTransport = EgpuTransport.UNKNOWN
    display_handoff: CapabilitySupport = CapabilitySupport.UNKNOWN
    audio_handoff: CapabilitySupport = CapabilitySupport.UNKNOWN
    internal_controller_suppression: CapabilitySupport = CapabilitySupport.UNKNOWN
    external_controller_promotion: CapabilitySupport = CapabilitySupport.UNKNOWN
    power_button_interception: CapabilitySupport = CapabilitySupport.UNKNOWN


@dataclass(frozen=True, slots=True)
class EgpuCapabilities:
    profile_id: str
    display_output: CapabilitySupport = CapabilitySupport.UNKNOWN
    audio_output: CapabilitySupport = CapabilitySupport.UNKNOWN
    sleep_behavior: SleepBehavior = SleepBehavior.UNTESTED
    removal_behavior: RemovalBehavior = RemovalBehavior.UNKNOWN


@dataclass(frozen=True, slots=True)
class EffectiveCapabilities:
    host_profile_id: str
    egpu_profile_id: str
    egpu_support: CapabilitySupport
    egpu_transport: EgpuTransport
    display_handoff: CapabilitySupport
    audio_handoff: CapabilitySupport
    internal_controller_suppression: CapabilitySupport
    external_controller_promotion: CapabilitySupport
    power_button_interception: CapabilitySupport
    sleep_behavior: SleepBehavior
    removal_behavior: RemovalBehavior

    @property
    def live_removal_allowed(self) -> bool:
        return self.removal_behavior is RemovalBehavior.LIVE_REMOVAL_VERIFIED


@dataclass(frozen=True, slots=True)
class TransitionRequest:
    request_id: str
    intent: RequestIntent
    source: RequestSource
    requested_at: str
    expected_generation: str

    def __post_init__(self) -> None:
        if not self.request_id or not self.requested_at or not self.expected_generation:
            raise ValueError("transition request identity and generation are required")


@dataclass(frozen=True, slots=True)
class PlannedStep:
    code: str
    deadline_ms: int
    requires_consent: bool = False

    def __post_init__(self) -> None:
        if not self.code:
            raise ValueError("planned step code is required")
        if self.deadline_ms <= 0:
            raise ValueError("planned step deadline must be positive")


@dataclass(frozen=True, slots=True)
class TransitionPlan:
    plan_id: str
    request_id: str
    observed_generation: str
    from_placement: PlacementState
    target_placement: PlacementState
    workflow_state: WorkflowState
    steps: tuple[PlannedStep, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.plan_id or not self.request_id or not self.observed_generation:
            raise ValueError("transition plan identity and generation are required")
        codes = tuple(step.code for step in self.steps)
        if len(codes) != len(set(codes)):
            raise ValueError("planned step codes must be unique")


@dataclass(frozen=True, slots=True)
class TransitionFailure:
    code: str
    message: str
    recoverable: bool
    action_required: bool = False


@dataclass(frozen=True, slots=True)
class RecoveryOutcome:
    attempted: bool
    verified: bool
    placement: PlacementState
    failure: TransitionFailure | None = None


@dataclass(frozen=True, slots=True)
class TransitionOutcome:
    kind: TransitionOutcomeKind
    placement: PlacementState
    workflow_state: WorkflowState
    failure: TransitionFailure | None = None
    recovery: RecoveryOutcome | None = None


UNKNOWN_HOST_CAPABILITIES = HostCapabilities(profile_id="unknown-host")
UNKNOWN_EGPU_CAPABILITIES = EgpuCapabilities(profile_id="unknown-egpu")


def combine_capability(
    host: CapabilitySupport, peripheral: CapabilitySupport
) -> CapabilitySupport:
    """Compose two required capabilities without promoting unknown evidence."""
    if CapabilitySupport.UNSUPPORTED in (host, peripheral):
        return CapabilitySupport.UNSUPPORTED
    if CapabilitySupport.UNKNOWN in (host, peripheral):
        return CapabilitySupport.UNKNOWN
    if CapabilitySupport.EXPERIMENTAL in (host, peripheral):
        return CapabilitySupport.EXPERIMENTAL
    return CapabilitySupport.VERIFIED


def compose_capabilities(
    host: HostCapabilities, egpu: EgpuCapabilities
) -> EffectiveCapabilities:
    return EffectiveCapabilities(
        host_profile_id=host.profile_id,
        egpu_profile_id=egpu.profile_id,
        egpu_support=host.egpu_support,
        egpu_transport=host.egpu_transport,
        display_handoff=combine_capability(host.display_handoff, egpu.display_output),
        audio_handoff=combine_capability(host.audio_handoff, egpu.audio_output),
        internal_controller_suppression=host.internal_controller_suppression,
        external_controller_promotion=host.external_controller_promotion,
        power_button_interception=host.power_button_interception,
        sleep_behavior=egpu.sleep_behavior,
        removal_behavior=egpu.removal_behavior,
    )

