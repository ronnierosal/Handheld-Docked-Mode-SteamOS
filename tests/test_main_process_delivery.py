from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from hdm.application.guarded_process_release import (  # noqa: E402
    GuardedProcessReleaseExecution,
    GuardedProcessReleasePreview,
    GuardedProcessReleaseStatus,
)
from hdm.application.snapshot import SnapshotReport  # noqa: E402
from hdm.application.docked_igpu_lifecycle import (  # noqa: E402
    DockedIgpuLifecycleStage,
    DockedIgpuLifecycleStatus,
)
from hdm.application.diagnostic_logging import (  # noqa: E402
    DiagnosticLoggingController,
)
from hdm.application.game_evidence_support import (  # noqa: E402
    SupportGameEvidence,
    SupportRenderEvidence,
)
from hdm.application.support_bundle import WakeDiagnosticsSupportStatus  # noqa: E402
from hdm.domain.control_plane import PlacementState  # noqa: E402
from hdm.domain.inference import infer_operating_mode  # noqa: E402
from hdm.domain.serialization import snapshot_from_dict  # noqa: E402
from hdm.domain.game_gpu_client import GameEgpuClientStatus  # noqa: E402
from hdm.domain.game_render_activity import GameRenderActivityStatus  # noqa: E402
from hdm.domain.game_runtime import GameRuntimeKind  # noqa: E402
from hdm.domain.models import EgpuResourceKind, GameState  # noqa: E402
from hdm.domain.process_release import (  # noqa: E402
    ProcessReleasePreview,
    ProcessReleasePreviewRow,
    ReleasePhase,
)


class Logger:
    def info(self, *args, **kwargs):
        pass

    def exception(self, *args, **kwargs):
        pass


class Service:
    def __init__(self):
        self.preview_calls = []
        self.executions = []
        self.acknowledgements = []

    def status(self):
        return GuardedProcessReleaseStatus("process_release.idle")

    def preview(
        self,
        phase,
        *,
        user_confirmed,
        graceful_receipt_token,
    ):
        self.preview_calls.append(
            (phase, user_confirmed, graceful_receipt_token)
        )
        return GuardedProcessReleasePreview(
            phase,
            ProcessReleasePreview(
                "approval_token_public_1" if user_confirmed else "",
                phase,
                120 if user_confirmed else 0,
                (
                    ProcessReleasePreviewRow(
                        "ordinary-client", (EgpuResourceKind.DRM_RENDER,)
                    ),
                ),
                1,
            ),
        )

    def execute(self, token):
        self.executions.append(token)
        return GuardedProcessReleaseExecution(
            False, "process_release.approval_invalid"
        )

    def acknowledge(self, operation_id):
        self.acknowledgements.append(operation_id)
        return operation_id == "operation-public-1"


class SupportEvidenceService:
    def __init__(self, *, external_unknown=False):
        self.calls = 0
        self.external_unknown = external_unknown

    def observe(self):
        self.calls += 1
        return SupportGameEvidence(
            GameState.RUNNING,
            True,
            GameEgpuClientStatus.ABSENT,
            0,
            "game_gpu.egpu_render_client_absent",
            SupportRenderEvidence(
                GameRenderActivityStatus.ACTIVE,
                GameRuntimeKind.PROTON,
                1,
                "render_activity.active",
                PlacementState.DOCKED_IGPU,
            ),
            (
                SupportRenderEvidence(
                    GameRenderActivityStatus.UNKNOWN,
                    GameRuntimeKind.UNKNOWN,
                    0,
                    "render_activity.binding_unverified",
                    PlacementState.UNKNOWN,
                )
                if self.external_unknown
                else SupportRenderEvidence(
                    GameRenderActivityStatus.NO_CLIENT,
                    GameRuntimeKind.PROTON,
                    0,
                    "render_activity.no_client",
                    PlacementState.DOCKED_IGPU,
                )
            ),
        )


class SnapshotApi:
    def __init__(self, *snapshots):
        self._snapshots = iter(snapshots)
        self.calls = 0

    def get_snapshot_report(self):
        self.calls += 1
        snapshot = next(self._snapshots)
        return SnapshotReport(snapshot, infer_operating_mode(snapshot))


class DockedIgpuScheduler:
    def __init__(self, *, acknowledgement=True):
        self.value = DockedIgpuLifecycleStatus(
            DockedIgpuLifecycleStage.ACTION_REQUIRED,
            "docked_igpu.game_identity_unverified",
            0,
            acknowledgement_required=True,
        )
        self.acknowledgement = acknowledgement
        self.acknowledge_calls = 0
        self.wake_calls = 0
        self.started = False
        self.stopped = False

    def status(self):
        return self.value

    def acknowledge_action(self):
        self.acknowledge_calls += 1
        return self.acknowledgement

    def wake(self):
        self.wake_calls += 1

    async def run(self):
        self.started = True
        try:
            await asyncio.Event().wait()
        finally:
            self.stopped = True


async def support_snapshot():
    return {
        "snapshot": {
            "schema_version": 3,
            "observed_at": "2026-08-31T00:00:00+00:00",
            "host_profile": "asus-rog-ally-x",
            "support_tier": "certified",
            "game_state": "running",
            "gpus": [],
            "displays": [],
            "gamescope": {},
            "disconnect_readiness": {},
            "sleep_guard": {},
            "blockers": [],
        },
        "diagnostics": {},
    }


def load_main_module():
    decky = types.ModuleType("decky")
    decky.DECKY_VERSION = "test"
    decky.DECKY_USER_HOME = str(ROOT)
    decky.logger = Logger()
    previous = sys.modules.get("decky")
    sys.modules["decky"] = decky
    try:
        spec = importlib.util.spec_from_file_location("hdm_test_main", ROOT / "main.py")
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        if previous is None:
            sys.modules.pop("decky", None)
        else:
            sys.modules["decky"] = previous


class MainProcessDeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_main_module()

    def plugin(self):
        plugin = self.module.Plugin()
        service = Service()
        plugin._process_release = service
        return plugin, service

    def plugin_with_diagnostic_logging(self):
        plugin, service = self.plugin()
        plugin._diagnostic_logging = DiagnosticLoggingController(
            plugin._events,
            monotonic=lambda: 100.0,
            boot_session_id=lambda: "boot-session-test",
        )
        return plugin, service

    def test_verified_topology_delta_is_recorded_without_recovery(self):
        plugin, service = self.plugin()
        portable = snapshot_from_dict(
            json.loads((ROOT / "tests" / "fixtures" / "portable.json").read_text())
        )
        docked = snapshot_from_dict(
            json.loads((ROOT / "tests" / "fixtures" / "tv-docked.json").read_text())
        )

        plugin._record_topology_observation(portable)
        plugin._record_topology_observation(docked)
        history = asyncio.run(plugin.get_action_history())

        self.assertEqual(service.preview_calls, [])
        self.assertEqual(service.executions, [])
        self.assertEqual(len(history["entries"]), 1)
        self.assertEqual(history["entries"][0]["kind"], "topology")
        self.assertEqual(history["entries"][0]["code"], "topology.egpu_attached")

    def test_snapshot_delivery_observes_existing_report_once_per_refresh(self):
        plugin, _service = self.plugin()
        portable = snapshot_from_dict(
            json.loads((ROOT / "tests" / "fixtures" / "portable.json").read_text())
        )
        docked = snapshot_from_dict(
            json.loads((ROOT / "tests" / "fixtures" / "tv-docked.json").read_text())
        )
        api = SnapshotApi(portable, docked)
        plugin._api = api

        asyncio.run(plugin.get_snapshot())
        asyncio.run(plugin.get_snapshot())
        history = asyncio.run(plugin.get_action_history())

        self.assertEqual(api.calls, 2)
        self.assertEqual(
            [entry["code"] for entry in history["entries"]],
            ["topology.egpu_attached"],
        )

    def test_preview_and_approval_use_enum_and_opaque_receipt_only(self):
        plugin, service = self.plugin()
        inspection = asyncio.run(plugin.preview_process_release("graceful"))
        approval = asyncio.run(plugin.approve_process_release("force", "receipt_public_1"))
        self.assertEqual(inspection["approval_token"], "")
        self.assertEqual(inspection["targets"][0]["name"], "ordinary-client")
        self.assertEqual(approval["approval_token"], "approval_token_public_1")
        self.assertEqual(
            service.preview_calls,
            [
                (ReleasePhase.GRACEFUL, False, ""),
                (ReleasePhase.FORCE, True, "receipt_public_1"),
            ],
        )
        encoded = json.dumps((inspection, approval)).lower()
        self.assertNotIn("pid", encoded)
        self.assertNotIn("instance", encoded)

    def test_invalid_phase_never_reaches_service(self):
        plugin, service = self.plugin()
        result = asyncio.run(plugin.approve_process_release("kill_everything"))
        self.assertFalse(result["ready"])
        self.assertEqual(result["phase"], "")
        self.assertEqual(service.preview_calls, [])

    def test_status_execute_and_exact_acknowledgement_are_bounded(self):
        plugin, service = self.plugin()
        status = asyncio.run(plugin.get_process_release_status())
        execution = asyncio.run(plugin.execute_process_release("approval_public_1"))
        rejected = asyncio.run(plugin.acknowledge_process_release("wrong"))
        accepted = asyncio.run(
            plugin.acknowledge_process_release("operation-public-1")
        )
        self.assertEqual(status["code"], "process_release.idle")
        self.assertEqual(execution["code"], "process_release.approval_invalid")
        self.assertFalse(execution["hardware_removal_authorized"])
        self.assertFalse(rejected["acknowledged"])
        self.assertTrue(accepted["acknowledged"])
        self.assertEqual(service.executions, ["approval_public_1"])

    def test_support_preview_runs_one_shot_identity_free_game_evidence(self):
        plugin, _service = self.plugin()
        evidence = SupportEvidenceService()
        plugin.get_snapshot = support_snapshot
        plugin._support_game_evidence_service = lambda: evidence

        result = asyncio.run(plugin.preview_support_bundle())
        payload = json.loads(result["preview_json"])
        rows = [
            event
            for event in payload["events"]
            if event["component"] == "game_evidence"
        ]

        self.assertEqual(evidence.calls, 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["code"], "game_evidence.captured")
        encoded = json.dumps(rows, sort_keys=True).lower()
        for private in ("appid", "scope", "pid", "renderd", "0000:", "stable_id"):
            self.assertNotIn(private, encoded)

    def test_support_preview_survives_game_evidence_failure(self):
        plugin, _service = self.plugin()
        plugin.get_snapshot = support_snapshot

        def unavailable():
            raise RuntimeError("private failure")

        plugin._support_game_evidence_service = unavailable
        result = asyncio.run(plugin.preview_support_bundle())
        payload = json.loads(result["preview_json"])

        self.assertTrue(result["preview_token"])
        self.assertIn(
            "game_evidence.unavailable",
            {event["code"] for event in payload["events"]},
        )

    def test_support_preview_marks_either_unknown_target_incomplete(self):
        plugin, _service = self.plugin()
        plugin.get_snapshot = support_snapshot
        plugin._support_game_evidence_service = lambda: SupportEvidenceService(
            external_unknown=True
        )

        result = asyncio.run(plugin.preview_support_bundle())
        payload = json.loads(result["preview_json"])
        rows = [
            event
            for event in payload["events"]
            if event["component"] == "game_evidence"
        ]

        self.assertEqual(rows[0]["code"], "game_evidence.incomplete")

    def test_support_preview_includes_categorical_wake_diagnostics_only(self):
        plugin, _service = self.plugin()
        plugin.get_snapshot = support_snapshot
        plugin._support_wake_diagnostics = lambda: WakeDiagnosticsSupportStatus(
            applicable=True,
            bridge_wakeup="enabled",
            function_wakeup_enabled=1,
            function_wakeup_disabled=2,
            function_wakeup_unknown=0,
            function_runtime_active=2,
            function_runtime_suspended=1,
            function_runtime_unknown=0,
            reason="wake.read_only_capability_observed",
        )

        result = asyncio.run(plugin.preview_support_bundle())
        payload = json.loads(result["preview_json"])
        encoded = json.dumps(payload, sort_keys=True).lower()

        self.assertEqual(payload["wake_diagnostics"]["bridge_wakeup"], "enabled")
        self.assertNotIn("0000:", encoded)
        self.assertNotIn("power/wakeup", encoded)

    def test_docked_igpu_status_is_categorical_and_identity_free(self):
        plugin, _service = self.plugin()
        unavailable = asyncio.run(plugin.get_docked_igpu_status())
        scheduler = DockedIgpuScheduler()
        plugin._docked_igpu_scheduler = scheduler

        observed = asyncio.run(plugin.get_docked_igpu_status())
        encoded = json.dumps(observed, sort_keys=True)

        self.assertEqual(unavailable["code"], "docked_igpu.lifecycle_unavailable")
        self.assertEqual(observed["stage"], "action_required")
        self.assertTrue(observed["acknowledgement_required"])
        for private in ("watch_id", "appid", "scope", "generation", "private"):
            self.assertNotIn(private, encoded.lower())

    def test_diagnostic_logging_requires_confirmation_and_allowlisted_duration(self):
        plugin, _service = self.plugin_with_diagnostic_logging()

        initial = asyncio.run(plugin.get_diagnostic_logging_status())
        unconfirmed = asyncio.run(
            plugin.enable_diagnostic_logging("2_hours", False)
        )
        invalid = asyncio.run(
            plugin.enable_diagnostic_logging("forever", True)
        )
        enabled = asyncio.run(
            plugin.enable_diagnostic_logging("30_minutes", True)
        )
        disabled = asyncio.run(plugin.disable_diagnostic_logging())

        self.assertFalse(initial["enabled"])
        self.assertEqual(
            unconfirmed["code"], "diagnostics.verbose_enable_rejected"
        )
        self.assertEqual(invalid["code"], "diagnostics.verbose_enable_rejected")
        self.assertTrue(enabled["enabled"])
        self.assertEqual(enabled["duration"], "30_minutes")
        self.assertEqual(enabled["remaining_seconds"], 1800)
        self.assertFalse(disabled["enabled"])
        self.assertEqual(disabled["code"], "diagnostics.verbose_disabled")

    def test_verbose_snapshot_event_is_opt_in_bounded_and_identity_free(self):
        plugin, _service = self.plugin_with_diagnostic_logging()
        sample = {
            "snapshot": {
                "game_state": "running",
                "support_tier": "certified",
                "blockers": [{"code": "test.blocker", "pid": 1234}],
                "gpus": [{"stable_id": "private-gpu"}],
            },
            "inference": {"mode": "docked_igpu"},
            "diagnostics": {"timings_ms": [{"stage": "snapshot_total"}]},
        }

        plugin._record_verbose_snapshot(sample)
        self.assertNotIn(
            "diagnostics.snapshot_observed",
            {event.code for event in plugin._events.snapshot()},
        )
        asyncio.run(plugin.enable_diagnostic_logging("2_hours", True))
        plugin._record_verbose_snapshot(sample)
        events = plugin._events.snapshot()
        verbose = [
            event for event in events if event.code == "diagnostics.snapshot_observed"
        ]
        encoded = json.dumps([event.details for event in verbose], sort_keys=True)

        self.assertEqual(len(verbose), 1)
        self.assertIn("test.blocker", encoded)
        self.assertIn("docked_igpu", encoded)
        for private in ("1234", "private-gpu", "stable_id", "pid"):
            self.assertNotIn(private, encoded)

    def test_audit_failure_cannot_hide_committed_logging_state(self):
        plugin, _service = self.plugin_with_diagnostic_logging()

        def audit_failure(**_kwargs):
            raise RuntimeError("private audit failure")

        plugin._diagnostic_logging.append = audit_failure
        enabled = asyncio.run(
            plugin.enable_diagnostic_logging("30_minutes", True)
        )
        self.assertTrue(enabled["enabled"])
        self.assertTrue(plugin._diagnostic_logging.status().enabled)

        disabled = asyncio.run(plugin.disable_diagnostic_logging())
        self.assertFalse(disabled["enabled"])
        self.assertFalse(plugin._diagnostic_logging.status().enabled)

    def test_docked_igpu_acknowledgement_wakes_only_after_acceptance(self):
        plugin, _service = self.plugin()
        scheduler = DockedIgpuScheduler()
        plugin._docked_igpu_scheduler = scheduler

        accepted = asyncio.run(plugin.acknowledge_docked_igpu_status())
        scheduler.acknowledgement = False
        rejected = asyncio.run(plugin.acknowledge_docked_igpu_status())

        self.assertTrue(accepted["acknowledged"])
        self.assertFalse(rejected["acknowledged"])
        self.assertEqual(scheduler.acknowledge_calls, 2)
        self.assertEqual(scheduler.wake_calls, 1)

    def test_docked_igpu_task_start_and_unload_are_owned_once(self):
        plugin, _service = self.plugin()
        scheduler = DockedIgpuScheduler()
        plugin._build_docked_igpu_scheduler = lambda: scheduler

        async def exercise():
            await plugin._start_docked_igpu_lifecycle()
            for _ in range(100):
                if scheduler.started:
                    break
                await asyncio.sleep(0.001)
            first_task = plugin._docked_igpu_task
            await plugin._start_docked_igpu_lifecycle()
            self.assertIs(plugin._docked_igpu_task, first_task)
            await plugin._stop_docked_igpu_lifecycle()

        asyncio.run(exercise())

        self.assertTrue(scheduler.started)
        self.assertTrue(scheduler.stopped)
        self.assertIsNone(plugin._docked_igpu_task)
        self.assertIsNone(plugin._docked_igpu_scheduler)

    def test_docked_igpu_supervisor_retries_transient_build_failure(self):
        plugin, _service = self.plugin()
        plugin._docked_igpu_retry_seconds = 0.001
        scheduler = DockedIgpuScheduler()
        attempts = 0

        def build():
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise RuntimeError("transient private failure")
            return scheduler

        plugin._build_docked_igpu_scheduler = build

        async def exercise():
            await plugin._start_docked_igpu_lifecycle()
            for _ in range(100):
                if scheduler.started:
                    break
                await asyncio.sleep(0.001)
            await plugin._stop_docked_igpu_lifecycle()

        asyncio.run(exercise())

        self.assertGreaterEqual(attempts, 2)
        self.assertTrue(scheduler.started)
        self.assertTrue(scheduler.stopped)

    def test_docked_igpu_supervisor_restarts_after_runner_failure(self):
        plugin, _service = self.plugin()
        plugin._docked_igpu_retry_seconds = 0.001

        class FailedScheduler(DockedIgpuScheduler):
            async def run(self):
                self.started = True
                raise RuntimeError("private runner failure")

        first = FailedScheduler()
        second = DockedIgpuScheduler()
        schedulers = [first, second]
        plugin._build_docked_igpu_scheduler = lambda: schedulers.pop(0)

        async def exercise():
            await plugin._start_docked_igpu_lifecycle()
            for _ in range(100):
                if second.started:
                    break
                await asyncio.sleep(0.001)
            await plugin._stop_docked_igpu_lifecycle()

        asyncio.run(exercise())

        self.assertTrue(first.started)
        self.assertTrue(second.started)
        self.assertTrue(second.stopped)


if __name__ == "__main__":
    unittest.main()
