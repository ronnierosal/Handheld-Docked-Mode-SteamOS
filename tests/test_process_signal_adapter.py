from __future__ import annotations

import signal
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from hdm.adapters.steamos.process_signal import PosixProcessSignalAdapter  # noqa: E402
from hdm.domain.models import EgpuResourceKind  # noqa: E402
from hdm.domain.process_release import ProcessReleaseTarget  # noqa: E402
from hdm.ports.process_signal import ProcessSignalAction  # noqa: E402


def target(pid: int = 100) -> ProcessReleaseTarget:
    return ProcessReleaseTarget(
        instance_id="ephemeral-instance",
        pid=pid,
        name="test-client",
        resources=(EgpuResourceKind.DRM_RENDER,),
    )


class PosixProcessSignalAdapterTests(unittest.TestCase):
    def test_maps_only_typed_graceful_and_force_actions(self):
        calls: list[tuple[int, int]] = []
        adapter = PosixProcessSignalAdapter(
            lambda pid, signal_number: calls.append((pid, signal_number)),
            platform_name="posix",
        )
        graceful = adapter.signal(target(), ProcessSignalAction.GRACEFUL_TERMINATE)
        force = adapter.signal(target(), ProcessSignalAction.FORCE_TERMINATE)
        self.assertEqual(
            calls,
            [
                (100, int(getattr(signal, "SIGTERM", 15))),
                (100, int(getattr(signal, "SIGKILL", 9))),
            ],
        )
        self.assertTrue(graceful.accepted)
        self.assertTrue(force.accepted)

    def test_missing_process_is_rescannable_not_a_success_claim(self):
        def missing(_pid, _signal_number):
            raise ProcessLookupError

        result = PosixProcessSignalAdapter(missing, platform_name="posix").signal(
            target(), ProcessSignalAction.GRACEFUL_TERMINATE
        )
        self.assertTrue(result.accepted)
        self.assertEqual(result.code, "signal.process_absent")

    def test_permission_and_os_errors_are_categorical(self):
        def denied(_pid, _signal_number):
            raise PermissionError("private detail")

        def failed(_pid, _signal_number):
            raise OSError("private detail")

        for operation, expected in (
            (denied, "signal.permission_denied"),
            (failed, "signal.os_error"),
        ):
            with self.subTest(expected=expected):
                result = PosixProcessSignalAdapter(
                    operation, platform_name="posix"
                ).signal(
                    target(), ProcessSignalAction.GRACEFUL_TERMINATE
                )
                self.assertFalse(result.accepted)
                self.assertEqual(result.code, expected)
                self.assertNotIn("private", result.code)

    def test_non_posix_platform_fails_closed_without_calling_kill(self):
        calls = []
        result = PosixProcessSignalAdapter(
            lambda pid, signal_number: calls.append((pid, signal_number)),
            platform_name="nt",
        ).signal(target(), ProcessSignalAction.GRACEFUL_TERMINATE)
        self.assertFalse(result.accepted)
        self.assertEqual(result.code, "signal.platform_unsupported")
        self.assertEqual(calls, [])

    def test_pid_one_empty_resources_and_duplicate_resources_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "identity"):
            target(1)
        with self.assertRaisesRegex(ValueError, "resources"):
            ProcessReleaseTarget("instance", 100, "client", ())
        with self.assertRaisesRegex(ValueError, "resources"):
            ProcessReleaseTarget(
                "instance",
                100,
                "client",
                (EgpuResourceKind.DRM_RENDER, EgpuResourceKind.DRM_RENDER),
            )


if __name__ == "__main__":
    unittest.main()
