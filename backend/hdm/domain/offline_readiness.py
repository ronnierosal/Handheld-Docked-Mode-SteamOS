"""Pure, deliberately conservative offline-play readiness classification.

This is a glanceable local assessment, not a promise that a game will work
offline.  Steam, a publisher launcher, DRM, anti-cheat, and the game itself
remain the authority at launch time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


MAX_BLOCKERS = 16
PUBLIC_REASON_CODES = frozenset(
    {
        "local_readiness_confirmed",
        "missing_local_content",
        "local_storage_unavailable",
        "install_integrity_unconfirmed",
        "game_not_installed",
        "download_pending",
        "update_pending",
        "cloud_save_pending",
        "cloud_save_conflict",
        "third_party_launcher",
        "drm",
        "anti_cheat",
        "game_owned_online_requirement",
        "install_unknown",
        "download_state_unknown",
        "steam_entitlement_unknown",
        "cloud_save_unknown",
    }
)


class OfflineReadinessStatus(StrEnum):
    READY_TO_TRY_OFFLINE = "ready_to_try_offline"
    NEEDS_ATTENTION = "needs_attention"
    ONLINE_CHECK_NEEDED = "online_check_needed"
    UNKNOWN = "unknown"


class InstallState(StrEnum):
    INSTALLED = "installed"
    NOT_INSTALLED = "not_installed"
    UNKNOWN = "unknown"


class DownloadState(StrEnum):
    CURRENT = "current"
    PENDING_DOWNLOAD = "pending_download"
    PENDING_UPDATE = "pending_update"
    UNKNOWN = "unknown"


class SteamEntitlementState(StrEnum):
    RECENT_SIGN_IN_AND_LICENSE = "recent_sign_in_and_license"
    SIGN_IN_OR_LICENSE_UNCONFIRMED = "sign_in_or_license_unconfirmed"
    UNKNOWN = "unknown"


class CloudSaveState(StrEnum):
    SYNCED = "synced"
    PENDING = "pending"
    CONFLICT = "conflict"
    UNKNOWN = "unknown"


class OnlineCheckRequirement(StrEnum):
    THIRD_PARTY_LAUNCHER = "third_party_launcher"
    DRM = "drm"
    ANTI_CHEAT = "anti_cheat"
    GAME_OWNED_ONLINE_REQUIREMENT = "game_owned_online_requirement"


class LocalOfflineBlocker(StrEnum):
    MISSING_LOCAL_CONTENT = "missing_local_content"
    LOCAL_STORAGE_UNAVAILABLE = "local_storage_unavailable"
    INSTALL_INTEGRITY_UNCONFIRMED = "install_integrity_unconfirmed"


@dataclass(frozen=True, slots=True)
class OfflineReadinessEvidence:
    """Categorical, local-only evidence for one game; no account data or paths."""

    install: InstallState = InstallState.UNKNOWN
    download: DownloadState = DownloadState.UNKNOWN
    steam_entitlement: SteamEntitlementState = SteamEntitlementState.UNKNOWN
    cloud_save: CloudSaveState = CloudSaveState.UNKNOWN
    local_blockers: tuple[LocalOfflineBlocker, ...] = field(default_factory=tuple)
    online_check_requirements: tuple[OnlineCheckRequirement, ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        if len(self.local_blockers) > MAX_BLOCKERS or len(
            self.online_check_requirements
        ) > MAX_BLOCKERS:
            raise ValueError("offline readiness evidence exceeds its bound")
        if len(set(self.local_blockers)) != len(self.local_blockers):
            raise ValueError("offline readiness local blockers are duplicated")
        if len(set(self.online_check_requirements)) != len(
            self.online_check_requirements
        ):
            raise ValueError("offline readiness online checks are duplicated")


@dataclass(frozen=True, slots=True)
class OfflineReadinessAssessment:
    status: OfflineReadinessStatus
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.status, OfflineReadinessStatus):
            raise ValueError("offline readiness status is invalid")
        if not self.reason_codes or len(self.reason_codes) > MAX_BLOCKERS:
            raise ValueError("offline readiness reasons are invalid")
        if len(set(self.reason_codes)) != len(self.reason_codes):
            raise ValueError("offline readiness reasons are duplicated")
        if not set(self.reason_codes).issubset(PUBLIC_REASON_CODES):
            raise ValueError("offline readiness reasons are not public codes")


def classify_offline_readiness(
    evidence: OfflineReadinessEvidence,
) -> OfflineReadinessAssessment:
    """Fail closed: incomplete evidence is never promoted to ready."""

    attention = _attention_reasons(evidence)
    if attention:
        return OfflineReadinessAssessment(
            OfflineReadinessStatus.NEEDS_ATTENTION, tuple(attention)
        )
    if evidence.online_check_requirements:
        return OfflineReadinessAssessment(
            OfflineReadinessStatus.ONLINE_CHECK_NEEDED,
            tuple(item.value for item in evidence.online_check_requirements),
        )
    unknown = _unknown_reasons(evidence)
    if unknown:
        return OfflineReadinessAssessment(OfflineReadinessStatus.UNKNOWN, tuple(unknown))
    return OfflineReadinessAssessment(
        OfflineReadinessStatus.READY_TO_TRY_OFFLINE,
        ("local_readiness_confirmed",),
    )


def offline_readiness_to_public_dict(
    assessment: OfflineReadinessAssessment,
) -> dict[str, Any]:
    """Serialize only categorical guidance; omit game, account, path, and time data."""

    return {
        "schema_version": 1,
        "status": assessment.status.value,
        "reason_codes": list(assessment.reason_codes),
    }


def _attention_reasons(evidence: OfflineReadinessEvidence) -> list[str]:
    reasons = [item.value for item in evidence.local_blockers]
    if evidence.install is InstallState.NOT_INSTALLED:
        reasons.append("game_not_installed")
    if evidence.download is DownloadState.PENDING_DOWNLOAD:
        reasons.append("download_pending")
    elif evidence.download is DownloadState.PENDING_UPDATE:
        reasons.append("update_pending")
    if evidence.cloud_save is CloudSaveState.PENDING:
        reasons.append("cloud_save_pending")
    elif evidence.cloud_save is CloudSaveState.CONFLICT:
        reasons.append("cloud_save_conflict")
    return reasons


def _unknown_reasons(evidence: OfflineReadinessEvidence) -> list[str]:
    reasons: list[str] = []
    if evidence.install is InstallState.UNKNOWN:
        reasons.append("install_unknown")
    if evidence.download is DownloadState.UNKNOWN:
        reasons.append("download_state_unknown")
    if evidence.steam_entitlement is not SteamEntitlementState.RECENT_SIGN_IN_AND_LICENSE:
        reasons.append("steam_entitlement_unknown")
    if evidence.cloud_save is CloudSaveState.UNKNOWN:
        reasons.append("cloud_save_unknown")
    return reasons
