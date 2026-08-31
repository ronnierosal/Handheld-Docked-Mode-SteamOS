"""Conservative runtime profile and capability resolution."""

from __future__ import annotations

from dataclasses import dataclass

from ..domain.control_plane import (
    EffectiveCapabilities,
    UNKNOWN_EGPU_CAPABILITIES,
    UNKNOWN_HOST_CAPABILITIES,
    compose_capabilities,
)
from ..domain.models import Confidence, GpuRole, ObservedSnapshot, SupportTier
from .ally_x import CAPABILITIES as ALLY_X_CAPABILITIES
from .ally_x import PROFILE_ID as ALLY_X_PROFILE_ID
from .gpd_g1 import CAPABILITIES as GPD_G1_CAPABILITIES


@dataclass(frozen=True, slots=True)
class ResolvedRuntimeProfiles:
    capabilities: EffectiveCapabilities
    exact_host: bool
    exact_egpu: bool
    egpu_stable_id: str = ""


def resolve_runtime_profiles(snapshot: ObservedSnapshot) -> ResolvedRuntimeProfiles:
    host = (
        ALLY_X_CAPABILITIES
        if snapshot.host_profile == ALLY_X_PROFILE_ID
        else UNKNOWN_HOST_CAPABILITIES
    )
    external = tuple(
        gpu
        for gpu in snapshot.gpus
        if gpu.role is GpuRole.EXTERNAL
        and gpu.present
        and gpu.confidence is Confidence.VERIFIED
        and gpu.stable_id.startswith("gpd-g1:")
    )
    exact_egpu = len(external) == 1 and snapshot.support_tier is SupportTier.CERTIFIED
    egpu = GPD_G1_CAPABILITIES if exact_egpu else UNKNOWN_EGPU_CAPABILITIES
    return ResolvedRuntimeProfiles(
        capabilities=compose_capabilities(host, egpu),
        exact_host=host is ALLY_X_CAPABILITIES,
        exact_egpu=exact_egpu,
        egpu_stable_id=external[0].stable_id if exact_egpu else "",
    )
