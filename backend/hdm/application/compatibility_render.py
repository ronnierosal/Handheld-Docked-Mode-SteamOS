"""Dormant compatibility-test consumer of exact DRM activity evidence."""

from __future__ import annotations

from typing import Protocol

from ..domain.compatibility_test import (
    CompatibilityTestSession,
    record_egpu_handoff_result,
    require_compatibility_action,
)
from ..domain.control_plane import PlacementState
from ..domain.game_compatibility import EgpuHandoffStatus, ObservedRenderGpu
from ..domain.game_render_activity import (
    GameRenderActivityEvidence,
    GameRenderActivityStatus,
)
from ..domain.game_session import ActiveGameIdentity


class RenderEvidencePort(Protocol):
    def observe(
        self, identity: ActiveGameIdentity, *, user_uid: int
    ) -> GameRenderActivityEvidence: ...


class CompatibilityRenderEvidenceCollector:
    """Record evidence only; catalog promotion still requires explicit review."""

    def __init__(self, renderer: RenderEvidencePort) -> None:
        self._renderer = renderer

    def record_external_handoff(
        self,
        session: CompatibilityTestSession,
        identity: ActiveGameIdentity,
        *,
        user_uid: int,
        now_ms: int,
    ) -> CompatibilityTestSession:
        baseline = session.baseline
        if (
            baseline is None
            or baseline.steam_app_id != identity.steam_app_id
            or baseline.render_gpu is not ObservedRenderGpu.INTERNAL
        ):
            return require_compatibility_action(
                session,
                "compatibility.render_baseline_mismatch",
                now_ms=now_ms,
            )
        try:
            evidence = self._renderer.observe(identity, user_uid=user_uid)
        except Exception:
            evidence = None
        if evidence is None or evidence.status is not GameRenderActivityStatus.ACTIVE:
            return require_compatibility_action(
                session,
                "compatibility.external_render_unverified",
                now_ms=now_ms,
            )
        if evidence.placement is not PlacementState.DOCKED_EGPU:
            return require_compatibility_action(
                session,
                "compatibility.external_placement_unverified",
                now_ms=now_ms,
            )
        return record_egpu_handoff_result(
            session,
            status=EgpuHandoffStatus.VERIFIED,
            observed_render_gpu=ObservedRenderGpu.EXTERNAL,
            observation_generation=evidence.evidence_generation,
            now_ms=now_ms,
        )
