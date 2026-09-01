from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from hdm.application.compatibility_test_lifecycle import (  # noqa: E402
    CompatibilityTestLifecycle,
    CompatibilityTestStart,
)
from hdm.application.compatibility_baseline import (  # noqa: E402
    CompatibilityBaselineCapture,
)
from hdm.application.diagnostic_logging import (  # noqa: E402
    DiagnosticLoggingController,
)
from hdm.application.support_bundle import BoundedEventLog  # noqa: E402
from hdm.domain.compatibility_test import (  # noqa: E402
    CompatibilityBaseline,
    CompatibilityTestOptions,
    CompatibilityTestStage,
)
from hdm.domain.control_plane import PlacementState  # noqa: E402
from hdm.domain.game_compatibility import (  # noqa: E402
    CompatibilityEvidenceKind,
    EgpuHandoffStatus,
    ObservedRenderGpu,
    SaveTestOutcome,
)
from hdm.domain.models import GameState  # noqa: E402


class Clock:
    def __init__(self, now=100):
        self.now = now

    def now_ms(self):
        return self.now


class SessionIds:
    def __init__(self):
        self.calls = 0

    def new_session_id(self):
        self.calls += 1
        return f"compat-lifecycle-{self.calls}"


class Authorization:
    def __init__(self, value=False):
        self.value = value
        self.calls = 0

    def hardware_test_authorized(self):
        self.calls += 1
        return self.value


class UserContext:
    def current_user_uid(self):
        return 1000


class BaselineCollector:
    def __init__(self, value):
        self.value = value
        self.user_uid = None

    def capture(self, *, user_uid):
        self.user_uid = user_uid
        if isinstance(self.value, Exception):
            raise self.value
        return self.value


def start_request(kind=CompatibilityEvidenceKind.SIMULATION):
    return CompatibilityTestStart(
        CompatibilityTestOptions(),
        kind,
        "steam-1234",
        "asus-rog-ally-x",
        "gpd-g1-rx7600mxt-titan-ridge",
        "0.2.0",
        "20260831",
    )


def baseline():
    return CompatibilityBaseline(
        "baseline-generation",
        PlacementState.PORTABLE,
        GameState.RUNNING,
        "1234",
        ObservedRenderGpu.INTERNAL,
    )


class CompatibilityTestLifecycleTests(unittest.TestCase):
    def lifecycle(self, *, authorized=False, baseline_collector=None):
        clock = Clock()
        events = BoundedEventLog()
        diagnostics = DiagnosticLoggingController(
            events, monotonic=lambda: 100.0, boot_session_id=lambda: "boot-test"
        )
        authorization = Authorization(authorized)
        return (
            CompatibilityTestLifecycle(
                diagnostics=diagnostics,
                clock=clock,
                session_ids=SessionIds(),
                hardware_authorization=authorization,
                baseline_collector=baseline_collector,
                user_context=UserContext() if baseline_collector is not None else None,
            ),
            clock,
            diagnostics,
            authorization,
        )

    def test_start_enables_bounded_logging_and_serializes_live_session(self):
        lifecycle, _clock, diagnostics, _authorization = self.lifecycle()

        started = lifecycle.start(start_request(), user_confirmed=True)

        self.assertEqual(started.stage, CompatibilityTestStage.AWAITING_BASELINE)
        self.assertTrue(diagnostics.status().enabled)
        with self.assertRaisesRegex(ValueError, "already active"):
            lifecycle.start(start_request(), user_confirmed=True)

    def test_terminal_action_required_disables_logging_without_a_catalog_write(self):
        lifecycle, _clock, diagnostics, _authorization = self.lifecycle()
        lifecycle.start(start_request(), user_confirmed=True)
        lifecycle.record_baseline(baseline())

        stopped = lifecycle.record_egpu_handoff(
            status=EgpuHandoffStatus.VERIFIED,
            observed_render_gpu=ObservedRenderGpu.EXTERNAL,
            observation_generation="baseline-generation",
        )

        self.assertEqual(stopped.stage, CompatibilityTestStage.ACTION_REQUIRED)
        self.assertFalse(diagnostics.status().enabled)
        self.assertEqual(stopped.reason_code, "compatibility.handoff_observation_stale")

    def test_finish_disables_logging_after_every_requested_result(self):
        lifecycle, _clock, diagnostics, _authorization = self.lifecycle()
        lifecycle.start(start_request(), user_confirmed=True)
        lifecycle.record_baseline(baseline())
        lifecycle.record_egpu_handoff(
            status=EgpuHandoffStatus.VERIFIED,
            observed_render_gpu=ObservedRenderGpu.EXTERNAL,
            observation_generation="external-generation",
        )
        lifecycle.record_save(
            outcome=SaveTestOutcome.MANUAL_SAVE_REQUIRED,
            observation_generation="save-generation",
        )

        finished = lifecycle.finish()

        self.assertEqual(finished.stage, CompatibilityTestStage.AWAITING_REVIEW)
        self.assertFalse(diagnostics.status().enabled)

    def test_status_expires_live_session_and_disables_logging(self):
        lifecycle, clock, diagnostics, _authorization = self.lifecycle()
        started = lifecycle.start(start_request(), user_confirmed=True)
        clock.now = started.expires_at_ms

        expired = lifecycle.status()

        self.assertEqual(expired.stage, CompatibilityTestStage.CANCELLED)
        self.assertEqual(expired.reason_code, "compatibility.expired")
        self.assertFalse(diagnostics.status().enabled)

        self.assertEqual(lifecycle.cancel().reason_code, "compatibility.expired")

    def test_hardware_evidence_needs_trusted_authorization_not_caller_data(self):
        lifecycle, _clock, diagnostics, authorization = self.lifecycle(authorized=False)

        with self.assertRaisesRegex(ValueError, "trusted-runner"):
            lifecycle.start(
                start_request(CompatibilityEvidenceKind.HARDWARE_TEST),
                user_confirmed=True,
            )

        self.assertEqual(authorization.calls, 1)
        self.assertIsNone(lifecycle.status())
        self.assertFalse(diagnostics.status().enabled)

    def test_observed_baseline_uses_trusted_context_and_stops_on_failure(self):
        collector = BaselineCollector(
            CompatibilityBaselineCapture(
                True, "compatibility.baseline_captured", baseline()
            )
        )
        lifecycle, _clock, diagnostics, _authorization = self.lifecycle(
            baseline_collector=collector
        )
        lifecycle.start(start_request(), user_confirmed=True)

        active = lifecycle.capture_observed_baseline()

        self.assertEqual(active.stage, CompatibilityTestStage.ACTIVE)
        self.assertEqual(collector.user_uid, 1000)
        self.assertTrue(diagnostics.status().enabled)

        unavailable, _clock, diagnostics, _authorization = self.lifecycle()
        unavailable.start(start_request(), user_confirmed=True)
        stopped = unavailable.capture_observed_baseline()
        self.assertEqual(stopped.stage, CompatibilityTestStage.ACTION_REQUIRED)
        self.assertEqual(
            stopped.reason_code, "compatibility.baseline_observer_unavailable"
        )
        self.assertFalse(diagnostics.status().enabled)


if __name__ == "__main__":
    unittest.main()
