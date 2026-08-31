"""Pure controller/audio handoff policy with verified fallback requirements."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .control_plane import CapabilitySupport, EffectiveCapabilities


class HandoffDirection(StrEnum):
    DOCK = "dock"
    UNDOCK = "undock"
    EXTERNAL_CONTROLLER_LOST = "external_controller_lost"


class ControllerDirective(StrEnum):
    KEEP_CURRENT = "keep_current"
    PROMOTE_EXTERNAL = "promote_external"
    SUPPRESS_BUILTIN = "suppress_builtin"
    RESTORE_BUILTIN = "restore_builtin"
    PROMOTE_BUILTIN = "promote_builtin"
    DISCONNECT_EXTERNAL = "disconnect_external"
    POWER_OFF_EXTERNAL = "power_off_external"
    ACTION_REQUIRED = "action_required"


class AudioOutput(StrEnum):
    INTERNAL = "internal"
    EXTERNAL = "external"
    OTHER_PORTABLE = "other_portable"
    UNKNOWN = "unknown"


class AudioDirective(StrEnum):
    KEEP_CURRENT = "keep_current"
    SELECT_EXTERNAL = "select_external"
    RESTORE_PORTABLE = "restore_portable"
    ACTION_REQUIRED = "action_required"


@dataclass(frozen=True, slots=True)
class ControllerHandoffObservation:
    builtin_available: bool | None
    builtin_input_verified: bool
    external_connected: bool | None
    external_input_verified: bool
    builtin_restore_verified: bool


@dataclass(frozen=True, slots=True)
class ControllerHandoffPolicy:
    suppress_builtin_when_docked: bool = False
    disconnect_external_when_undocked: bool = False
    power_off_external_when_undocked: bool = False


@dataclass(frozen=True, slots=True)
class ControllerHandoffDecision:
    directives: tuple[ControllerDirective, ...]
    blockers: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.directives:
            raise ValueError("controller handoff decision requires a directive")
        if ControllerDirective.ACTION_REQUIRED in self.directives and not self.blockers:
            raise ValueError("controller action-required decision needs blockers")
        if ControllerDirective.SUPPRESS_BUILTIN in self.directives and (
            ControllerDirective.PROMOTE_EXTERNAL not in self.directives
        ):
            raise ValueError("built-in suppression requires external promotion")


@dataclass(frozen=True, slots=True)
class AudioHandoffObservation:
    current_output: AudioOutput
    current_output_usable_verified: bool
    external_output_available: bool | None
    external_output_verified: bool
    portable_output_available: bool | None
    portable_output_verified: bool
    rollback_output_verified: bool


@dataclass(frozen=True, slots=True)
class AudioHandoffDecision:
    directives: tuple[AudioDirective, ...]
    blockers: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.directives:
            raise ValueError("audio handoff decision requires a directive")
        if AudioDirective.ACTION_REQUIRED in self.directives and not self.blockers:
            raise ValueError("audio action-required decision needs blockers")


def plan_controller_handoff(
    direction: HandoffDirection,
    observation: ControllerHandoffObservation,
    capabilities: EffectiveCapabilities,
    policy: ControllerHandoffPolicy = ControllerHandoffPolicy(),
) -> ControllerHandoffDecision:
    if direction in {HandoffDirection.UNDOCK, HandoffDirection.EXTERNAL_CONTROLLER_LOST}:
        blockers: list[str] = []
        if observation.builtin_available is not True:
            blockers.append("controller.builtin_unavailable_or_unknown")
        if not observation.builtin_input_verified:
            blockers.append("controller.builtin_input_unverified")
        if not observation.builtin_restore_verified:
            blockers.append("controller.builtin_restore_unverified")
        if blockers:
            return ControllerHandoffDecision(
                (ControllerDirective.ACTION_REQUIRED,),
                tuple(blockers),
            )
        directives = [
            ControllerDirective.RESTORE_BUILTIN,
            ControllerDirective.PROMOTE_BUILTIN,
        ]
        if direction is HandoffDirection.UNDOCK and observation.external_connected is True:
            if policy.power_off_external_when_undocked:
                if capabilities.external_controller_power_off is CapabilitySupport.VERIFIED:
                    directives.append(ControllerDirective.POWER_OFF_EXTERNAL)
                elif (
                    policy.disconnect_external_when_undocked
                    and capabilities.external_controller_disconnect is CapabilitySupport.VERIFIED
                ):
                    directives.append(ControllerDirective.DISCONNECT_EXTERNAL)
            elif (
                policy.disconnect_external_when_undocked
                and capabilities.external_controller_disconnect is CapabilitySupport.VERIFIED
            ):
                directives.append(ControllerDirective.DISCONNECT_EXTERNAL)
        return ControllerHandoffDecision(tuple(directives), ())

    if observation.external_connected is False:
        if observation.builtin_available is True and observation.builtin_input_verified:
            return ControllerHandoffDecision((ControllerDirective.KEEP_CURRENT,), ())
        return ControllerHandoffDecision(
            (ControllerDirective.ACTION_REQUIRED,),
            ("controller.no_verified_input",),
        )
    blockers = []
    if observation.external_connected is not True:
        blockers.append("controller.external_presence_unknown")
    if not observation.external_input_verified:
        blockers.append("controller.external_input_unverified")
    if capabilities.external_controller_promotion is not CapabilitySupport.VERIFIED:
        blockers.append("capability.external_controller_promotion_unverified")
    if blockers:
        return ControllerHandoffDecision(
            (ControllerDirective.ACTION_REQUIRED,),
            tuple(blockers),
        )
    directives = [ControllerDirective.PROMOTE_EXTERNAL]
    if policy.suppress_builtin_when_docked:
        if (
            capabilities.internal_controller_suppression is CapabilitySupport.VERIFIED
            and observation.builtin_restore_verified
            and observation.builtin_available is True
            and observation.builtin_input_verified
        ):
            directives.append(ControllerDirective.SUPPRESS_BUILTIN)
        else:
            return ControllerHandoffDecision(
                (ControllerDirective.PROMOTE_EXTERNAL,),
                ("controller.suppression_recovery_unverified",),
            )
    return ControllerHandoffDecision(tuple(directives), ())


def plan_audio_handoff(
    direction: HandoffDirection,
    observation: AudioHandoffObservation,
    capabilities: EffectiveCapabilities,
) -> AudioHandoffDecision:
    if direction is HandoffDirection.EXTERNAL_CONTROLLER_LOST:
        return AudioHandoffDecision((AudioDirective.KEEP_CURRENT,), ())
    if capabilities.audio_handoff is not CapabilitySupport.VERIFIED:
        return AudioHandoffDecision(
            (AudioDirective.KEEP_CURRENT, AudioDirective.ACTION_REQUIRED),
            ("capability.audio_handoff_unverified",),
        )
    if not observation.rollback_output_verified:
        return AudioHandoffDecision(
            (AudioDirective.KEEP_CURRENT, AudioDirective.ACTION_REQUIRED),
            ("audio.rollback_unverified",),
        )
    if direction is HandoffDirection.DOCK:
        if observation.external_output_available is True and observation.external_output_verified:
            return AudioHandoffDecision((AudioDirective.SELECT_EXTERNAL,), ())
        if observation.current_output_usable_verified:
            return AudioHandoffDecision(
                (AudioDirective.KEEP_CURRENT,),
                ("audio.external_unavailable_or_unverified",),
            )
        return AudioHandoffDecision(
            (AudioDirective.ACTION_REQUIRED,),
            ("audio.no_verified_output",),
        )
    if observation.portable_output_available is True and observation.portable_output_verified:
        return AudioHandoffDecision((AudioDirective.RESTORE_PORTABLE,), ())
    return AudioHandoffDecision(
        (AudioDirective.KEEP_CURRENT, AudioDirective.ACTION_REQUIRED),
        ("audio.portable_output_unavailable_or_unverified",),
    )
