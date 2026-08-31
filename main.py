"""Root Decky delivery adapter for the read-only HDM diagnostics API."""

from __future__ import annotations

import asyncio
import os
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path

import decky


PLUGIN_ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = PLUGIN_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from hdm.adapters.steamos.discovery import SteamOsDiscovery  # noqa: E402
from hdm.adapters.steamos.commands import UserServiceCommandRunner  # noqa: E402
from hdm.adapters.steamos.gamescope import GamescopeDiscovery  # noqa: E402
from hdm.adapters.steamos.gamescope_user import resolve_gamescope_user  # noqa: E402
from hdm.adapters.steamos.sleep_inhibitor import (  # noqa: E402
    G1SleepGuardHardwareDiscovery,
    SleepGuardController,
)
from hdm.adapters.steamos.process_signal import PosixProcessSignalAdapter  # noqa: E402
from hdm.adapters.steamos.version_info import SteamOsVersionDiscovery  # noqa: E402
from hdm.api import DiagnosticsApi  # noqa: E402
from hdm.adapters.transition_runtime import (  # noqa: E402
    SnapshotTransitionObservationAdapter,
    SystemMonotonicClock,
)
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
    SupportBundlePreviewStore,
    SupportBundleService,
)
from hdm.delivery.support_export import SupportBundleFileWriter  # noqa: E402
from hdm.delivery.gamescope_integration import GamescopeIntegrationStore  # noqa: E402
from hdm.delivery.process_release import (  # noqa: E402
    execution_to_payload,
    preview_to_payload,
    status_to_payload,
)
from hdm.delivery.runtime_state import RootOwnedRuntimeState  # noqa: E402
from hdm.delivery.transition_journal_store import FileTransitionJournalStore  # noqa: E402
from hdm.domain.process_release import ReleasePhase  # noqa: E402


class Plugin:
    def __init__(self) -> None:
        self._sleep_guard = SleepGuardController()
        self._sleep_hardware = G1SleepGuardHardwareDiscovery()
        self._discovery = SteamOsDiscovery(
            sleep_guard_status=self._sleep_guard.status
        )
        self._api = DiagnosticsApi(self._discovery)
        self._sleep_guard_task: asyncio.Task[None] | None = None
        self._last_sleep_guard_log: tuple[str, bool, str] | None = None
        self._events = BoundedEventLog()
        self._support_bundles = SupportBundleService()
        self._support_previews = SupportBundlePreviewStore()
        self._support_writer = SupportBundleFileWriter()
        self._presentation_approvals = PresentationActivationApprovalStore()
        self._process_approvals = ProcessReleaseApprovalStore()
        self._process_receipts = GracefulReleaseReceiptStore()
        self._process_release: GuardedProcessReleaseService | None = None
        self._version_info = SteamOsVersionDiscovery().scan()

    async def get_snapshot(self) -> dict[str, object]:
        """Return the existing privacy-safe, read-only diagnostics payload."""
        return await asyncio.to_thread(self._api.get_snapshot)

    async def preview_support_bundle(self) -> dict[str, object]:
        """Return a redacted preview and one-time approval token."""
        report = await self.get_snapshot()
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

    async def preview_presentation_preparation(self) -> dict[str, object]:
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

    async def approve_presentation_preparation(self) -> dict[str, object]:
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

    async def get_process_release_status(self) -> dict[str, object]:
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
        self._sleep_guard_task = asyncio.create_task(self._sleep_guard_loop())

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
        if self._sleep_guard_task is not None:
            self._sleep_guard_task.cancel()
            try:
                await self._sleep_guard_task
            except asyncio.CancelledError:
                pass
            self._sleep_guard_task = None
        status = await asyncio.to_thread(self._sleep_guard.close)
        decky.logger.info("HDM sleep guard released: active=%s", status.active)

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
