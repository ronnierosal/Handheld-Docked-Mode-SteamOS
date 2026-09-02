"""Pure, non-authorizing HDMI-CEC TV-wake feasibility and result contract."""
from dataclasses import dataclass
from enum import StrEnum

class TvWakeState(StrEnum):
    UNSUPPORTED = "unsupported"
    UNAVAILABLE = "unavailable"
    ATTEMPT_ELIGIBLE = "attempt_eligible"
    ATTEMPTED_UNVERIFIED = "attempted_unverified"
    VERIFIED_AWAKE = "verified_awake"
    FAILED_OR_UNKNOWN = "failed_or_unknown"

@dataclass(frozen=True, slots=True)
class TvWakeEvidence:
    profile_support: bool | None
    adapter_configured: bool
    exact_external_display_before: bool
    attempt_recorded: bool = False
    external_display_verified_after: bool = False
    adapter_result: bool | None = None

def assess_tv_wake(evidence: TvWakeEvidence) -> TvWakeState:
    if evidence.profile_support is False:
        return TvWakeState.UNSUPPORTED
    if evidence.profile_support is not True or not evidence.adapter_configured:
        return TvWakeState.UNAVAILABLE
    if not evidence.exact_external_display_before:
        return TvWakeState.FAILED_OR_UNKNOWN if evidence.attempt_recorded else TvWakeState.UNAVAILABLE
    if not evidence.attempt_recorded:
        return TvWakeState.ATTEMPT_ELIGIBLE
    if evidence.adapter_result is False:
        return TvWakeState.FAILED_OR_UNKNOWN
    if evidence.adapter_result is True and evidence.external_display_verified_after:
        return TvWakeState.VERIFIED_AWAKE
    return TvWakeState.ATTEMPTED_UNVERIFIED
