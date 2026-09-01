"""Root Decky delivery adapter for the read-only HDM diagnostics API."""

from __future__ import annotations

import asyncio
import os
import socket
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

import decky


PLUGIN_ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = PLUGIN_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from hdm.adapters.steamos.discovery import SteamOsDiscovery  # noqa: E402
from hdm.adapters.steamos.drm import DrmDiscovery  # noqa: E402
from hdm.adapters.steamos.pci import PciUsb4Discovery  # noqa: E402
from hdm.adapters.steamos.wake_diagnostics import WakeDiagnosticsDiscovery  # noqa: E402
from hdm.adapters.steamos.commands import UserServiceCommandRunner  # noqa: E402
from hdm.adapters.steamos.gamescope import GamescopeDiscovery  # noqa: E402
from hdm.adapters.steamos.gamescope_session import (  # noqa: E402
    GamescopeSessionObservationAdapter,
)
from hdm.adapters.steamos.gamescope_user import resolve_gamescope_user  # noqa: E402
from hdm.adapters.steamos.sleep_inhibitor import (  # noqa: E402
    G1SleepGuardHardwareDiscovery,
    SleepGuardController,
)
from hdm.adapters.steamos.process_signal import PosixProcessSignalAdapter  # noqa: E402
from hdm.adapters.game_runtime import CgroupProcGameRuntimeAdapter  # noqa: E402
from hdm.adapters.game_session import (  # noqa: E402
    GameScopeSessionObservationAdapter,
    UserBoundGameScopeScanAdapter,
)
from hdm.adapters.drm_engine_activity import (  # noqa: E402
    ProcfsDrmEngineCounterAdapter,
)
from hdm.adapters.steamos.game_render_binding import (  # noqa: E402
    AllyInternalDrmRenderBindingResolver,
    GpdG1DrmRenderBindingResolver,
)
from hdm.adapters.steamos.game_scopes import SystemdGameScopeDiscovery  # noqa: E402
from hdm.adapters.steamos.version_info import SteamOsVersionDiscovery  # noqa: E402
from hdm.adapters.steamos.peripherals import (  # noqa: E402
    SteamOsPeripheralObservationAdapter,
    peripheral_status_to_public_payload,
)
from hdm.api import DiagnosticsApi  # noqa: E402
from hdm.adapters.transition_runtime import (  # noqa: E402
    BoundedDeadlineWaiter,
    SnapshotTransitionObservationAdapter,
    SystemMonotonicClock,
    versioned_snapshot_observation,
)
from hdm.application.game_evidence_support import (  # noqa: E402
    SupportGameEvidenceService,
)
from hdm.application.game_gpu_client import GameEgpuClientEvidenceService  # noqa: E402
from hdm.application.game_render_activity import (  # noqa: E402
    GameRenderActivityComparisonService,
)
from hdm.application.diagnostic_logging import (  # noqa: E402
    DiagnosticLoggingController,
    DiagnosticLoggingDuration,
    DiagnosticVerbosity,
)
from hdm.application.action_history import project_action_history  # noqa: E402
from hdm.application.snapshot import report_to_public_dict  # noqa: E402
from hdm.application.attach_readiness import AttachReadinessLifecycle  # noqa: E402
from hdm.application.topology_event_detection import (  # noqa: E402
    TopologyDetectionStatus,
    detect_topology_event,
)
from hdm.application.docked_igpu_exit import DockedIgpuGameExitWatcher  # noqa: E402
from hdm.application.docked_igpu_lifecycle import DockedIgpuWatchLifecycle  # noqa: E402
from hdm.application.docked_igpu_promotion import DockedIgpuPromotionFacade  # noqa: E402
from hdm.application.presentation_activation import (  # noqa: E402
    PresentationActivationApprovalStore,
    PresentationActivationService,
)
from hdm.application.guarded_process_release import (  # noqa: E402
    GuardedProcessReleaseService,
)
from hdm.application.process_release import (  # noqa: E402
    GracefulReleaseReceiptStore,
    ProcessReleaseApprovalStore,
)
from hdm.application.process_release_replay import (  # noqa: E402
    ProcessReleaseJournalRecovery,
    ProcessReleaseRunner,
)
from hdm.application.support_bundle import (  # noqa: E402
    BoundedEventLog,
    SupportBundle,
    SupportBundleContext,
    SupportBundlePreviewStore,
    SupportBundleService,
    WakeDiagnosticsSupportStatus,
)
from hdm.delivery.support_export import SupportBundleFileWriter  # noqa: E402
from hdm.delivery.gamescope_integration import GamescopeIntegrationStore  # noqa: E402
from hdm.delivery.process_release import (  # noqa: E402
    execution_to_payload,
    preview_to_payload,
    status_to_payload,
)
from hdm.delivery.game_evidence_support import (  # noqa: E402
    game_evidence_to_event_details,
)
from hdm.delivery.diagnostic_logging import (  # noqa: E402
    diagnostic_logging_status_to_payload,
)
from hdm.delivery.build_info import load_public_build_info  # noqa: E402
from hdm.delivery.action_history import action_history_to_payload  # noqa: E402
from hdm.delivery.attach_readiness import attach_readiness_to_payload  # noqa: E402
from hdm.delivery.docked_igpu_lifecycle import lifecycle_status_to_payload  # noqa: E402
from hdm.delivery.peripheral_support import peripheral_support_status  # noqa: E402
from hdm.delivery.docked_igpu_scheduler import (  # noqa: E402
    DockedIgpuLifecycleScheduler,
)
from hdm.delivery.runtime_state import RootOwnedRuntimeState  # noqa: E402
from hdm.delivery.transition_journal_store import FileTransitionJournalStore  # noqa: E402
from hdm.domain.process_release import ReleasePhase  # noqa: E402
from hdm.profiles.gpd_g1 import match_gpd_g1  # noqa: E402


class Plugin:
    def __init__(self) -> None:
        self._sleep_guard = SleepGuardController()
        self._sleep_hardware = G1SleepGuardHardwareDiscovery()
        self._discovery = SteamOsDiscovery(
            sleep_guard_status=self._sleep_guard.status
        )
        self._api = DiagnosticsApi(self._discovery)
        self._peripherals = SteamOsPeripheralObservationAdapter()
        self._sleep_guard_task: asyncio.Task[None] | None = None
        self._docked_igpu_scheduler: DockedIgpuLifecycleScheduler | None = None
        self._docked_igpu_task: asyncio.Task[None] | None = None
        self._docked_igpu_retry_seconds = 30.0
        self._last_docked_igpu_lifecycle_code = ""
        self._last_sleep_guard_log: tuple[str, bool, str] | None = None
        self._events = BoundedEventLog()
        self._topology_lock = threading.Lock()
        self._topology_observation = None
        self._attach_readiness = AttachReadinessLifecycle()
        self._diagnostic_logging = DiagnosticLoggingController(
            self._events,
            boot_session_id=self._boot_session_id,
        )
        self._support_bundles = SupportBundleService()
        self._support_previews = SupportBundlePreviewStore()
        self._support_writer = SupportBundleFileWriter()
        self._presentation_approvals = PresentationActivationApprovalStore()
        self._process_approvals = ProcessReleaseApprovalStore()
        self._process_receipts = GracefulReleaseReceiptStore()
        self._process_release: GuardedProcessReleaseService | None = None
        self._version_info = SteamOsVersionDiscovery().scan()
        self._build_info = load_public_build_info(PLUGIN_ROOT)

    async def get_snapshot(self, _request: object = None) -> dict[str, object]:
        """Return the existing privacy-safe, read-only diagnostics payload."""
        report = await asyncio.to_thread(self._api.get_snapshot_report)
        payload = report_to_public_dict(report)
        payload["diagnostics"]["build"] = self._build_info
        attach_status = await asyncio.to_thread(
            self._record_topology_observation, report.snapshot
        )
        payload["attach_readiness"] = attach_readiness_to_payload(attach_status)
        await asyncio.to_thread(self._record_verbose_snapshot, payload)
        return payload

    def _record_topology_observation(self, snapshot):
        """Log only verified snapshot deltas; never execute recovery from them."""
        current = versioned_snapshot_observation(snapshot)
        with self._topology_lock:
            previous = self._topology_observation
            self._topology_observation = current
        detection = detect_topology_event(previous, current)
        status = self._attach_readiness.update(detection, current)
        if detection.status is not TopologyDetectionStatus.DETECTED:
            return status
        self._events.append(
            severity="info",
            code=detection.reason_code,
            component="topology",
            stage="observation",
        )
        return status

    async def get_peripheral_status(self, _request: object = None) -> dict[str, object]:
        """Read identity-free controller/audio evidence without any handoff action."""
        try:
            observed = await asyncio.to_thread(self._peripherals.observe)
            return peripheral_status_to_public_payload(observed)
        except Exception:
            return {
                "schema_version": 1,
                "controller": {"complete": False, "exact": False, "builtin_available": None, "external_connected": None, "code": "controller.observation_unavailable"},
                "audio": {"complete": False, "exact": False, "external_available": None, "portable_available": None, "code": "audio.observation_unavailable"},
            }

    async def get_action_history(self, _request: object = None) -> dict[str, object]:
        """Return the bounded, identity-free projection of existing HDM events."""
        try:
            return await asyncio.to_thread(
                lambda: action_history_to_payload(
                    project_action_history(self._events.snapshot())
                )
            )
        except Exception:
            return {"schema_version": 1, "entries": []}

    async def get_diagnostic_logging_status(self, _request: object = None) -> dict[str, object]:
        """Return bounded, identity-free status for the opt-in verbose session."""

        try:
            status = await asyncio.to_thread(self._diagnostic_logging.status)
            return diagnostic_logging_status_to_payload(status)
        except Exception:
            return self._diagnostic_logging_unavailable()

    async def enable_diagnostic_logging(
        self, duration: str, user_confirmed: bool
    ) -> dict[str, object]:
        """Enable only one allowlisted, explicitly confirmed ephemeral duration."""

        try:
            selected = DiagnosticLoggingDuration(duration)
            status = await asyncio.to_thread(
                self._diagnostic_logging.enable,
                selected,
                user_confirmed=user_confirmed is True,
            )
            try:
                self._diagnostic_logging.append(
                    verbosity=DiagnosticVerbosity.NORMAL,
                    severity="info",
                    code="diagnostics.verbose_enabled",
                    component="diagnostics",
                    stage="consent",
                    details={"duration": selected.value},
                )
            except Exception:
                pass
            return diagnostic_logging_status_to_payload(status)
        except Exception:
            return self._diagnostic_logging_unavailable(
                "diagnostics.verbose_enable_rejected"
            )

    async def disable_diagnostic_logging(self, _request: object = None) -> dict[str, object]:
        """Disable verbose collection immediately without deleting normal events."""

        try:
            status = await asyncio.to_thread(self._diagnostic_logging.disable)
            try:
                self._diagnostic_logging.append(
                    verbosity=DiagnosticVerbosity.NORMAL,
                    severity="info",
                    code="diagnostics.verbose_disabled",
                    component="diagnostics",
                    stage="consent",
                )
            except Exception:
                pass
            return diagnostic_logging_status_to_payload(status)
        except Exception:
            return self._diagnostic_logging_unavailable()

    def _record_verbose_snapshot(self, payload: dict[str, object]) -> None:
        snapshot = payload.get("snapshot")
        inference = payload.get("inference")
        diagnostics = payload.get("diagnostics")
        if not isinstance(snapshot, dict):
            return
        blocker_codes = []
        blockers = snapshot.get("blockers")
        if isinstance(blockers, list):
            blocker_codes = [
                str(item.get("code", "unknown"))
                for item in blockers[:32]
                if isinstance(item, dict)
            ]
        mode = (
            str(inference.get("mode", "unknown"))
            if isinstance(inference, dict)
            else "unknown"
        )
        timing_count = (
            len(diagnostics.get("timings_ms", ()))
            if isinstance(diagnostics, dict)
            and isinstance(diagnostics.get("timings_ms"), list)
            else 0
        )
        self._diagnostic_logging.append(
            verbosity=DiagnosticVerbosity.VERBOSE,
            severity="info",
            code="diagnostics.snapshot_observed",
            component="diagnostics",
            stage="snapshot",
            details={
                "mode": mode,
                "game_state": str(snapshot.get("game_state", "unknown")),
                "support_tier": str(snapshot.get("support_tier", "unknown")),
                "blocker_codes": blocker_codes,
                "timing_count": timing_count,
            },
        )

    @staticmethod
    def _diagnostic_logging_unavailable(
        code: str = "diagnostics.verbose_status_unavailable",
    ) -> dict[str, object]:
        return {
            "schema_version": 1,
            "enabled": False,
            "mode": "off",
            "duration": "",
            "remaining_seconds": None,
            "code": code,
        }

    @staticmethod
    def _boot_session_id() -> str:
        return Path("/proc/sys/kernel/random/boot_id").read_text(
            encoding="ascii"
        ).strip()

    async def get_docked_igpu_status(self, _request: object = None) -> dict[str, object]:
        """Return only categorical state from the read-only natural-exit watch."""

        scheduler = self._docked_igpu_scheduler
        if scheduler is None:
            return {
                "schema_version": 1,
                "stage": "idle",
                "code": "docked_igpu.lifecycle_unavailable",
                "poll_after_ms": 15000,
                "inspection_available": False,
                "acknowledgement_required": False,
            }
        return lifecycle_status_to_payload(scheduler.status())

    async def acknowledge_docked_igpu_status(self, _request: object = None) -> dict[str, object]:
        """Acknowledge only a terminal read-only watch; never approve a transition."""

        scheduler = self._docked_igpu_scheduler
        if scheduler is None:
            return {"schema_version": 1, "acknowledged": False}
        try:
            acknowledged = await asyncio.to_thread(
                scheduler.acknowledge_action
            )
        except Exception:
            acknowledged = False
        if acknowledged:
            scheduler.wake()
        return {"schema_version": 1, "acknowledged": acknowledged}

    async def preview_support_bundle(self, _request: object = None) -> dict[str, object]:
        """Return a redacted preview and one-time approval token."""
        report = await self.get_snapshot()
        peripheral_status = None
        try:
            peripheral = await asyncio.to_thread(self._peripherals.observe)
            peripheral_status = peripheral_support_status(peripheral)
        except Exception:
            pass
        try:
            wake_diagnostics = await asyncio.to_thread(self._support_wake_diagnostics)
        except Exception:
            wake_diagnostics = None
        context = SupportBundleContext(
            peripheral_status=peripheral_status,
            wake_diagnostics=wake_diagnostics,
        )
        await asyncio.to_thread(self._record_support_game_evidence)
        self._events.append(
            severity="info",
            code="support.preview_created",
            component="support",
            stage="preview",
        )
        bundle = await asyncio.to_thread(
            self._support_bundles.build,
            report,
            self._events.snapshot(),
            self._support_versions(),
            self._sensitive_values(),
            context,
        )
        preview = self._support_previews.issue(bundle)
        return {
            "schema_version": 1,
            "preview_token": preview.token,
            "preview_json": bundle.json_text,
            "size_bytes": bundle.size_bytes,
            "event_count": bundle.event_count,
            "manifest": dict(bundle.payload["manifest"]),
        }

    @staticmethod
    def _support_wake_diagnostics() -> WakeDiagnosticsSupportStatus:
        """Read exact G1 wake capability state for an explicit support preview."""
        pci = PciUsb4Discovery()
        g1 = match_gpd_g1(DrmDiscovery().scan(), pci.scan_pci(), pci.scan_usb4())
        observed = WakeDiagnosticsDiscovery().observe(
            g1.root_bdf if g1.verified else "",
            g1.pci_functions if g1.verified else (),
        )
        return WakeDiagnosticsSupportStatus(
            applicable=observed.applicable,
            bridge_wakeup=observed.bridge_wakeup.value,
            function_wakeup_enabled=observed.function_wakeup_enabled,
            function_wakeup_disabled=observed.function_wakeup_disabled,
            function_wakeup_unknown=observed.function_wakeup_unknown,
            function_runtime_active=observed.function_runtime_active,
            function_runtime_suspended=observed.function_runtime_suspended,
            function_runtime_unknown=observed.function_runtime_unknown,
            reason=observed.reason or "wake.observation_unavailable",
        )

    async def save_support_bundle(self, preview_token: str) -> dict[str, object]:
        """Save only the exact bundle represented by a one-time preview token."""
        bundle = self._support_previews.consume(preview_token)
        result = await asyncio.to_thread(self._write_support_bundle, bundle)
        self._events.append(
            severity="info",
            code="support.bundle_saved",
            component="support",
            stage="save",
            details={"size_bytes": bundle.size_bytes},
        )
        return result

    def _record_support_game_evidence(self) -> None:
        try:
            evidence = self._support_game_evidence_service().observe()
            details = game_evidence_to_event_details(evidence)
            unavailable = (
                not evidence.identity_exact
                or evidence.internal_render.status.value == "unknown"
                or evidence.external_render.status.value == "unknown"
            )
            self._events.append(
                severity="warning" if unavailable else "info",
                code=(
                    "game_evidence.incomplete"
                    if unavailable
                    else "game_evidence.captured"
                ),
                component="game_evidence",
                stage="support_preview",
                details=details,
            )
        except Exception:
            self._events.append(
                severity="warning",
                code="game_evidence.unavailable",
                component="game_evidence",
                stage="support_preview",
            )

    def _support_game_evidence_service(self) -> SupportGameEvidenceService:
        resolution = resolve_gamescope_user(GamescopeDiscovery().scan())
        if not resolution.ok or resolution.context is None:
            raise ValueError("Gamescope user is unavailable")
        user_uid = resolution.context.uid
        snapshots = SnapshotTransitionObservationAdapter(self._discovery)
        runtime = CgroupProcGameRuntimeAdapter()
        counters = ProcfsDrmEngineCounterAdapter()
        sessions = GameScopeSessionObservationAdapter(
            UserBoundGameScopeScanAdapter(
                SystemdGameScopeDiscovery(),
                user_uid,
            )
        )
        return SupportGameEvidenceService(
            sessions=sessions,
            egpu_clients=GameEgpuClientEvidenceService(
                runtime=runtime,
                snapshots=snapshots,
            ),
            render_comparison=GameRenderActivityComparisonService(
                runtime=runtime,
                snapshots=snapshots,
                internal_binding=AllyInternalDrmRenderBindingResolver(),
                external_binding=GpdG1DrmRenderBindingResolver(),
                counters=counters,
                waiter=BoundedDeadlineWaiter(),
            ),
            user_uid=user_uid,
            verify_user=self._gamescope_user_matches,
        )

    @staticmethod
    def _gamescope_user_matches(expected_uid: int) -> bool:
        resolution = resolve_gamescope_user(GamescopeDiscovery().scan())
        return bool(
            resolution.ok
            and resolution.context is not None
            and resolution.context.uid == expected_uid
        )

    async def preview_presentation_preparation(self, _request: object = None) -> dict[str, object]:
        """Inspect the reversible integration without writing or restarting."""
        try:
            preview = await asyncio.to_thread(
                self._presentation_service().preview,
                user_confirmed=False,
            )
            return {
                "schema_version": 1,
                "ready": preview.already_ready,
                "blockers": list(preview.blockers),
                "confirmation_required": not preview.blockers,
            }
        except Exception:
            return {
                "schema_version": 1,
                "ready": False,
                "blockers": ["gamescope.user_unavailable"],
                "confirmation_required": False,
            }

    async def approve_presentation_preparation(self, _request: object = None) -> dict[str, object]:
        """Issue one exact approval after the controller confirmation action."""
        try:
            preview = await asyncio.to_thread(
                self._presentation_service().preview,
                user_confirmed=True,
            )
            return {
                "schema_version": 1,
                "approval_token": preview.token,
                "ready": preview.already_ready,
                "blockers": list(preview.blockers),
            }
        except Exception:
            return {
                "schema_version": 1,
                "approval_token": "",
                "ready": False,
                "blockers": ["activation.approval_failed"],
            }

    async def prepare_presentation_integration(
        self, approval_token: str
    ) -> dict[str, object]:
        """Prepare only the approved reversible integration; never restart."""
        try:
            outcome = await asyncio.to_thread(
                self._presentation_service().execute,
                approval_token,
            )
        except Exception:
            return {
                "schema_version": 1,
                "prepared": False,
                "changed": False,
                "code": "activation.user_unavailable",
                "rollback_attempted": False,
                "rollback_succeeded": False,
            }
        self._events.append(
            severity="info" if outcome.prepared else "warning",
            code=outcome.code,
            component="presentation",
            stage="preparation",
            details={
                "prepared": outcome.prepared,
                "changed": outcome.changed,
                "rollback_attempted": outcome.rollback_attempted,
                "rollback_succeeded": outcome.rollback_succeeded,
            },
        )
        return {
            "schema_version": 1,
            "prepared": outcome.prepared,
            "changed": outcome.changed,
            "code": outcome.code,
            "rollback_attempted": outcome.rollback_attempted,
            "rollback_succeeded": outcome.rollback_succeeded,
        }

    async def get_process_release_status(self, _request: object = None) -> dict[str, object]:
        """Return only categorical durable release state and acknowledgement ID."""
        try:
            status = await asyncio.to_thread(self._process_service().status)
            return status_to_payload(status)
        except Exception:
            return {
                "schema_version": 1,
                "code": "process_release.service_unavailable",
                "acknowledgement_required": False,
                "action_required": True,
                "acknowledgement_id": "",
                "durable": False,
            }

    async def preview_process_release(
        self,
        phase: str,
        force_receipt_token: str = "",
    ) -> dict[str, object]:
        """Inspect exact eligible clients without creating signal authority."""
        try:
            release_phase = ReleasePhase(phase)
            preview = await asyncio.to_thread(
                self._process_service().preview,
                release_phase,
                user_confirmed=False,
                graceful_receipt_token=force_receipt_token,
            )
            return preview_to_payload(preview)
        except Exception:
            return self._process_preview_failure(phase)

    async def approve_process_release(
        self,
        phase: str,
        force_receipt_token: str = "",
    ) -> dict[str, object]:
        """Issue one exact signal approval after controller confirmation."""
        try:
            release_phase = ReleasePhase(phase)
            preview = await asyncio.to_thread(
                self._process_service().preview,
                release_phase,
                user_confirmed=True,
                graceful_receipt_token=force_receipt_token,
            )
            return preview_to_payload(preview)
        except Exception:
            return self._process_preview_failure(phase)

    async def execute_process_release(
        self, approval_token: str
    ) -> dict[str, object]:
        """Execute only a consumed approval through the guarded release runner."""
        try:
            outcome = await asyncio.to_thread(
                self._process_service().execute,
                approval_token,
            )
            payload = execution_to_payload(outcome)
            self._events.append(
                severity="warning" if outcome.action_required else "info",
                code=outcome.code,
                component="process_release",
                stage="execution",
                details={
                    "accepted": outcome.accepted,
                    "action_required": outcome.action_required,
                    "remaining_client_count": payload["remaining_client_count"],
                },
            )
            return payload
        except Exception:
            return {
                "schema_version": 1,
                "accepted": False,
                "code": "process_release.service_unavailable",
                "acknowledgement_id": "",
                "status": "",
                "software_blockers_cleared": False,
                "hardware_removal_authorized": False,
                "remaining_client_count": None,
                "force_receipt_token": "",
                "action_required": True,
            }

    async def acknowledge_process_release(
        self, acknowledgement_id: str
    ) -> dict[str, object]:
        """Clear only an exact terminal process-release operation."""
        try:
            acknowledged = await asyncio.to_thread(
                self._process_service().acknowledge,
                acknowledgement_id,
            )
        except Exception:
            acknowledged = False
        return {"schema_version": 1, "acknowledged": acknowledged}

    async def _main(self) -> None:
        self._events.append(
            severity="info",
            code="plugin.started",
            component="lifecycle",
            stage="startup",
        )
        try:
            recovery = await asyncio.to_thread(
                self._process_service().recover_interrupted
            )
            if recovery.action_required:
                self._events.append(
                    severity="warning",
                    code=recovery.code,
                    component="process_release",
                    stage="startup_recovery",
                    details={"durable": recovery.durable},
                )
        except Exception:
            self._events.append(
                severity="error",
                code="process_release.startup_recovery_unavailable",
                component="process_release",
                stage="startup_recovery",
            )
        try:
            await self._reconcile_sleep_guard()
            payload = await self.get_snapshot()
            snapshot = payload["snapshot"]
            inference = payload["inference"]
            blocker_codes = [item["code"] for item in snapshot["blockers"]]
            decky.logger.info(
                "HDM diagnostics ready: mode=%s game=%s support=%s blockers=%s",
                inference["mode"],
                snapshot["game_state"],
                snapshot["support_tier"],
                blocker_codes,
            )
            self._events.append(
                severity="info",
                code="diagnostics.ready",
                component="discovery",
                stage="startup",
                details={
                    "mode": inference["mode"],
                    "game_state": snapshot["game_state"],
                    "support_tier": snapshot["support_tier"],
                    "blocker_codes": blocker_codes,
                },
            )
        except Exception:
            decky.logger.exception("HDM initial read-only snapshot failed")
            self._events.append(
                severity="error",
                code="diagnostics.initial_failed",
                component="discovery",
                stage="startup",
            )
        await self._start_docked_igpu_lifecycle()
        self._sleep_guard_task = asyncio.create_task(self._sleep_guard_loop())

    async def _start_docked_igpu_lifecycle(self) -> None:
        if self._docked_igpu_task is not None:
            return
        self._docked_igpu_task = asyncio.create_task(
            self._docked_igpu_supervisor_loop()
        )

    async def _docked_igpu_supervisor_loop(self) -> None:
        while True:
            try:
                scheduler = await asyncio.to_thread(
                    self._build_docked_igpu_scheduler
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                self._record_docked_igpu_lifecycle(
                    "docked_igpu.lifecycle_unavailable", "warning"
                )
                await asyncio.sleep(self._docked_igpu_retry_seconds)
                continue
            self._docked_igpu_scheduler = scheduler
            self._record_docked_igpu_lifecycle(
                "docked_igpu.lifecycle_started", "info"
            )
            try:
                await scheduler.run()
                self._record_docked_igpu_lifecycle(
                    "docked_igpu.lifecycle_stopped", "warning"
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                self._record_docked_igpu_lifecycle(
                    "docked_igpu.lifecycle_failed", "warning"
                )
            finally:
                self._docked_igpu_scheduler = None
            await asyncio.sleep(self._docked_igpu_retry_seconds)

    def _record_docked_igpu_lifecycle(self, code: str, severity: str) -> None:
        if code == self._last_docked_igpu_lifecycle_code:
            return
        self._last_docked_igpu_lifecycle_code = code
        self._events.append(
            severity=severity,
            code=code,
            component="docked_igpu",
            stage="runtime",
        )

    def _build_docked_igpu_scheduler(self) -> DockedIgpuLifecycleScheduler:
        resolution = resolve_gamescope_user(GamescopeDiscovery().scan())
        if not resolution.ok or resolution.context is None:
            raise ValueError("Gamescope user is unavailable")
        snapshots = SnapshotTransitionObservationAdapter(self._discovery)
        games = GameScopeSessionObservationAdapter(
            UserBoundGameScopeScanAdapter(
                SystemdGameScopeDiscovery(),
                resolution.context.uid,
            )
        )
        watcher = DockedIgpuGameExitWatcher(
            snapshots=snapshots,
            games=games,
            gamescope_sessions=GamescopeSessionObservationAdapter(
                GamescopeDiscovery()
            ),
            clock=SystemMonotonicClock(),
        )
        promotion = DockedIgpuPromotionFacade(watcher=watcher)
        return DockedIgpuLifecycleScheduler(
            DockedIgpuWatchLifecycle(
                promotion,
                poll_interval_ms=5000,
                idle_poll_interval_ms=15000,
            )
        )

    async def _reconcile_sleep_guard(self) -> None:
        presence = await asyncio.to_thread(self._sleep_hardware.observe_presence)
        status = await asyncio.to_thread(self._sleep_guard.reconcile, presence)
        current = (presence.value, status.active, status.error)
        if current != self._last_sleep_guard_log:
            decky.logger.info(
                "HDM sleep guard: presence=%s active=%s error=%s",
                presence.value,
                status.active,
                bool(status.error),
            )
            self._events.append(
                severity="warning" if status.error else "info",
                code="sleep_guard.state_changed",
                component="sleep_guard",
                stage="reconcile",
                details={
                    "presence": presence.value,
                    "active": status.active,
                    "error": bool(status.error),
                },
            )
            self._last_sleep_guard_log = current

    async def _sleep_guard_loop(self) -> None:
        while True:
            try:
                await self._reconcile_sleep_guard()
            except Exception:
                decky.logger.exception("HDM sleep guard reconciliation failed")
                self._events.append(
                    severity="error",
                    code="sleep_guard.reconcile_failed",
                    component="sleep_guard",
                    stage="reconcile",
                )
            await asyncio.sleep(1)

    async def _unload(self) -> None:
        self._events.append(
            severity="info",
            code="plugin.unloading",
            component="lifecycle",
            stage="shutdown",
        )
        await self._stop_docked_igpu_lifecycle()
        if self._sleep_guard_task is not None:
            self._sleep_guard_task.cancel()
            try:
                await self._sleep_guard_task
            except asyncio.CancelledError:
                pass
            self._sleep_guard_task = None
        status = await asyncio.to_thread(self._sleep_guard.close)
        decky.logger.info("HDM sleep guard released: active=%s", status.active)

    async def _stop_docked_igpu_lifecycle(self) -> None:
        task = self._docked_igpu_task
        self._docked_igpu_task = None
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception:
                self._events.append(
                    severity="warning",
                    code="docked_igpu.lifecycle_close_incomplete",
                    component="docked_igpu",
                    stage="shutdown",
                )
        self._docked_igpu_scheduler = None

    def _support_versions(self) -> dict[str, str]:
        return {
            "hdm": "0.2.0",
            "decky": str(getattr(decky, "DECKY_VERSION", "unknown")),
            "steamos": self._version_info.steamos,
            "kernel": self._version_info.kernel,
        }

    @staticmethod
    def _sensitive_values() -> tuple[str, ...]:
        home = str(getattr(decky, "DECKY_USER_HOME", ""))
        username = os.environ.get("DECKY_USER", "")
        return tuple(
            value
            for value in (home, Path(home).name if home else "", username, socket.gethostname())
            if value
        )

    def _write_support_bundle(self, bundle: SupportBundle) -> dict[str, object]:
        raw_home = Path(str(getattr(decky, "DECKY_USER_HOME", "")))
        result = self._support_writer.save(raw_home, bundle)
        return {
            "ok": True,
            "relative_path": result.relative_path,
            "size_bytes": result.size_bytes,
        }

    def _presentation_service(self) -> PresentationActivationService:
        resolution = resolve_gamescope_user(GamescopeDiscovery().scan())
        if not resolution.ok or resolution.context is None:
            raise ValueError("Gamescope user is unavailable")
        integration = GamescopeIntegrationStore(
            plugin_root=PLUGIN_ROOT,
            user=resolution.context,
        )
        return PresentationActivationService(
            observations=SnapshotTransitionObservationAdapter(self._discovery),
            integration=integration,
            commands=UserServiceCommandRunner(),
            resolve_user=lambda: resolve_gamescope_user(GamescopeDiscovery().scan()),
            approvals=self._presentation_approvals,
        )

    def _process_service(self) -> GuardedProcessReleaseService:
        if self._process_release is not None:
            return self._process_release
        state_root = RootOwnedRuntimeState().ensure()
        journal = FileTransitionJournalStore(state_root)
        observations = SnapshotTransitionObservationAdapter(self._discovery)
        occurred_at = lambda: datetime.now(timezone.utc).isoformat()
        recovery = ProcessReleaseJournalRecovery(
            journal,
            occurred_at=occurred_at,
        )
        runner = ProcessReleaseRunner(
            observations,
            PosixProcessSignalAdapter(),
            SystemMonotonicClock(),
            journal_store=journal,
            occurred_at=occurred_at,
        )
        self._process_release = GuardedProcessReleaseService(
            observations=observations,
            approvals=self._process_approvals,
            receipts=self._process_receipts,
            runner=runner,
            journal_store=journal,
            recovery=recovery,
        )
        return self._process_release

    @staticmethod
    def _process_preview_failure(phase: str) -> dict[str, object]:
        return {
            "schema_version": 1,
            "phase": phase if phase in {item.value for item in ReleasePhase} else "",
            "ready": False,
            "approval_token": "",
            "expires_in_seconds": 0,
            "targets": [],
            "protected_client_count": 0,
            "blockers": ["process_release.service_unavailable"],
            "confirmation_required": False,
        }
