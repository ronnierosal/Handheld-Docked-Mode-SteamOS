"""One-owner lifecycle for the dormant, non-mutating Compatibility Test Mode.

This coordinates pure session policy with temporary diagnostic logging. It has
no Decky RPC, catalog writer, game mechanism, or hardware-transition authority.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Protocol

from ..domain.compatibility_test import (
    CompatibilityBaseline,
    CompatibilityTestOptions,
    CompatibilityTestSession,
    CompatibilityTestStage,
    cancel_compatibility_test,
    finish_compatibility_test,
    record_compatibility_baseline,
    record_egpu_handoff_result,
    record_save_result,
    reconcile_compatibility_expiry,
    require_compatibility_action,
    start_compatibility_test,
)
from ..domain.game_compatibility import (
    CompatibilityEvidenceKind,
    EgpuHandoffStatus,
    ObservedRenderGpu,
    SaveTestOutcome,
)
from ..ports.transition import MonotonicClockPort
from .diagnostic_logging import (
    DiagnosticLoggingController,
    DiagnosticLoggingDuration,
)
from .compatibility_baseline import CompatibilityBaselineCapture


class CompatibilityHardwareAuthorizationPort(Protocol):
    """Trusted-runner boundary; never represent this as a frontend boolean."""

    def hardware_test_authorized(self) -> bool: ...


class CompatibilitySessionIdPort(Protocol):
    def new_session_id(self) -> str: ...


class CompatibilityBaselinePort(Protocol):
    def capture(self, *, user_uid: int) -> CompatibilityBaselineCapture: ...


class CompatibilityUserContextPort(Protocol):
    def current_user_uid(self) -> int: ...


@dataclass(frozen=True, slots=True)
class CompatibilityTestStart:
    options: CompatibilityTestOptions
    evidence_kind: CompatibilityEvidenceKind
    game_catalog_id: str
    host_profile_id: str
    egpu_profile_id: str
    hdm_version: str
    steamos_version: str


class CompatibilityTestLifecycle:
    """Serialize one ephemeral session and honor its logging directives exactly."""

    def __init__(
        self,
        *,
        diagnostics: DiagnosticLoggingController,
        clock: MonotonicClockPort,
        session_ids: CompatibilitySessionIdPort,
        hardware_authorization: CompatibilityHardwareAuthorizationPort,
        baseline_collector: CompatibilityBaselinePort | None = None,
        user_context: CompatibilityUserContextPort | None = None,
    ) -> None:
        self._diagnostics = diagnostics
        self._clock = clock
        self._session_ids = session_ids
        self._hardware_authorization = hardware_authorization
        self._baseline_collector = baseline_collector
        self._user_context = user_context
        self._session: CompatibilityTestSession | None = None
        self._lock = threading.Lock()

    def status(self) -> CompatibilityTestSession | None:
        with self._lock:
            self._reconcile_locked()
            return self._session

    def start(
        self, request: CompatibilityTestStart, *, user_confirmed: bool
    ) -> CompatibilityTestSession:
        with self._lock:
            self._reconcile_locked()
            if self._is_live_locked():
                raise ValueError("compatibility test session is already active")
            authorized = self._hardware_authorized_locked(request.evidence_kind)
            self._session = start_compatibility_test(
                session_id=self._session_ids.new_session_id(),
                options=request.options,
                evidence_kind=request.evidence_kind,
                game_catalog_id=request.game_catalog_id,
                host_profile_id=request.host_profile_id,
                egpu_profile_id=request.egpu_profile_id,
                hdm_version=request.hdm_version,
                steamos_version=request.steamos_version,
                user_confirmed=user_confirmed,
                hardware_test_authorized=authorized,
                now_ms=self._now_locked(),
            )
            self._apply_logging_directives_locked()
            return self._session

    def record_baseline(
        self, baseline: CompatibilityBaseline
    ) -> CompatibilityTestSession | None:
        return self._advance(lambda session, now: record_compatibility_baseline(
            session, baseline, now_ms=now
        ))

    def capture_observed_baseline(self) -> CompatibilityTestSession | None:
        """Capture through injected read-only ports; delivery never supplies identity."""
        with self._lock:
            self._reconcile_locked()
            if self._session is None:
                return None
            if self._session.stage is not CompatibilityTestStage.AWAITING_BASELINE:
                return self._session
            capture = self._capture_baseline_locked()
            now = self._now_locked()
            self._session = (
                record_compatibility_baseline(
                    self._session, capture.baseline, now_ms=now
                )
                if capture.accepted and capture.baseline is not None
                else require_compatibility_action(
                    self._session, capture.code, now_ms=now
                )
            )
            self._apply_logging_directives_locked()
            return self._session

    def record_egpu_handoff(
        self,
        *,
        status: EgpuHandoffStatus,
        observed_render_gpu: ObservedRenderGpu,
        observation_generation: str,
    ) -> CompatibilityTestSession | None:
        return self._advance(lambda session, now: record_egpu_handoff_result(
            session,
            status=status,
            observed_render_gpu=observed_render_gpu,
            observation_generation=observation_generation,
            now_ms=now,
        ))

    def record_save(
        self,
        *,
        outcome: SaveTestOutcome,
        observation_generation: str,
    ) -> CompatibilityTestSession | None:
        return self._advance(lambda session, now: record_save_result(
            session,
            outcome=outcome,
            observation_generation=observation_generation,
            now_ms=now,
        ))

    def finish(self) -> CompatibilityTestSession | None:
        return self._advance(
            lambda session, now: finish_compatibility_test(session, now_ms=now)
        )

    def cancel(self) -> CompatibilityTestSession | None:
        with self._lock:
            self._reconcile_locked()
            if not self._is_live_locked():
                return self._session
            self._session = cancel_compatibility_test(self._session)
            self._apply_logging_directives_locked()
            return self._session

    def _advance(self, action) -> CompatibilityTestSession | None:
        with self._lock:
            self._reconcile_locked()
            if not self._is_live_locked():
                return self._session
            self._session = action(self._session, self._now_locked())
            self._apply_logging_directives_locked()
            return self._session

    def _reconcile_locked(self) -> None:
        if self._session is None:
            return
        self._session = reconcile_compatibility_expiry(
            self._session, now_ms=self._now_locked()
        )
        self._apply_logging_directives_locked()

    def _apply_logging_directives_locked(self) -> None:
        if self._session is None:
            return
        if self._session.stage is CompatibilityTestStage.AWAITING_BASELINE:
            if not self._diagnostics.status().enabled:
                self._diagnostics.enable(
                    DiagnosticLoggingDuration.HOURS_2, user_confirmed=True
                )
            return
        if self._session.stage in {
            CompatibilityTestStage.AWAITING_REVIEW,
            CompatibilityTestStage.COMPLETED,
            CompatibilityTestStage.CANCELLED,
            CompatibilityTestStage.ACTION_REQUIRED,
        }:
            self._diagnostics.disable()

    def _is_live_locked(self) -> bool:
        return self._session is not None and self._session.stage in {
            CompatibilityTestStage.AWAITING_BASELINE,
            CompatibilityTestStage.ACTIVE,
        }

    def _hardware_authorized_locked(self, kind: CompatibilityEvidenceKind) -> bool:
        if kind is not CompatibilityEvidenceKind.HARDWARE_TEST:
            return False
        try:
            return self._hardware_authorization.hardware_test_authorized() is True
        except Exception:
            return False

    def _capture_baseline_locked(self) -> CompatibilityBaselineCapture:
        if self._baseline_collector is None or self._user_context is None:
            return CompatibilityBaselineCapture(
                False, "compatibility.baseline_observer_unavailable"
            )
        try:
            user_uid = self._user_context.current_user_uid()
            result = self._baseline_collector.capture(user_uid=user_uid)
        except Exception:
            result = None
        if not isinstance(result, CompatibilityBaselineCapture):
            return CompatibilityBaselineCapture(
                False, "compatibility.baseline_observer_unavailable"
            )
        return result

    def _now_locked(self) -> int:
        value = self._clock.now_ms()
        if not isinstance(value, int) or value < 0:
            raise ValueError("compatibility test clock is invalid")
        return value
