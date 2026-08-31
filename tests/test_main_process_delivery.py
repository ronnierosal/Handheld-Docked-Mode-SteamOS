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
from hdm.application.game_evidence_support import (  # noqa: E402
    SupportGameEvidence,
    SupportRenderEvidence,
)
from hdm.domain.control_plane import PlacementState  # noqa: E402
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


if __name__ == "__main__":
    unittest.main()
