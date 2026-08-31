from __future__ import annotations

import dataclasses
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from hdm.adapters.drm_engine_activity import (  # noqa: E402
    ProcfsDrmEngineCounterAdapter,
)
from hdm.application.game_render_activity import (  # noqa: E402
    GameRenderActivityEvidenceService,
)
from hdm.domain.game_render_activity import (  # noqa: E402
    DrmEngineClientCounters,
    DrmEngineCounterSample,
    DrmRenderBinding,
    GameRenderActivityStatus,
)
from hdm.domain.game_runtime import (  # noqa: E402
    ActiveGameRuntimeObservation,
    GameProcessInstance,
    GameRuntimeKind,
)
from hdm.domain.game_session import ActiveGameIdentity  # noqa: E402
from hdm.domain.models import GameState  # noqa: E402
from hdm.domain.serialization import snapshot_from_dict  # noqa: E402
from hdm.ports.transition import VersionedObservation  # noqa: E402


FIXTURES = ROOT / "tests" / "fixtures"
EGPU_ID = "gpd-g1:0123456789abcdef"
BINDING = DrmRenderBinding(EGPU_ID, "0000:08:00.0", "/dev/dri/renderD131")
IDENTITY = ActiveGameIdentity("1234", ("app-steam-app1234-test.scope",))
PROCESS = GameProcessInstance(101, 500, 1, "game", False)


def stat_line(start: int) -> str:
    fields = ["S", "1", *("0" for _ in range(48))]
    fields[19] = str(start)
    return f"101 (game process) {' '.join(fields)}\n"


def fdinfo(*, gfx: int, compute: int = 0, pdev: str = "0000:08:00.0") -> str:
    return (
        "pos:\t0\n"
        "drm-driver:\tamdgpu\n"
        f"drm-pdev:\t{pdev}\n"
        "drm-client-id:\t7\n"
        f"drm-engine-gfx:\t{gfx} ns\n"
        f"drm-engine-compute:\t{compute} ns\n"
    )


class DrmEngineAdapterTests(unittest.TestCase):
    def fixture(self, root: Path, *, info: str, target="/dev/dri/renderD131"):
        process = root / "101"
        (process / "fd").mkdir(parents=True)
        (process / "fdinfo").mkdir()
        (process / "stat").write_text(stat_line(500), encoding="utf-8")
        descriptor = process / "fd" / "5"
        descriptor.write_text("", encoding="utf-8")
        (process / "fdinfo" / "5").write_text(info, encoding="utf-8")
        return ProcfsDrmEngineCounterAdapter(
            proc_root=root,
            fd_target_reader=lambda path: target,
        )

    def test_exact_fdinfo_returns_private_engine_counters(self):
        with tempfile.TemporaryDirectory() as directory:
            adapter = self.fixture(Path(directory), info=fdinfo(gfx=100, compute=5))
            result = adapter.sample((PROCESS,), BINDING)

        self.assertTrue(result.complete)
        self.assertEqual(len(result.clients), 1)
        self.assertEqual(result.clients[0].identity, (101, 500, 7))
        self.assertEqual(
            dict(result.clients[0].counters_ns), {"compute": 5, "gfx": 100}
        )
        self.assertNotIn(BINDING.render_node, repr(result))

    def test_wrong_pci_identity_and_missing_counter_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            adapter = self.fixture(
                Path(directory), info=fdinfo(gfx=100, pdev="0000:09:00.0")
            )
            wrong = adapter.sample((PROCESS,), BINDING)
        with tempfile.TemporaryDirectory() as directory:
            adapter = self.fixture(
                Path(directory),
                info=(
                    "drm-driver: amdgpu\n"
                    "drm-pdev: 0000:08:00.0\n"
                    "drm-client-id: 7\n"
                ),
            )
            incomplete = adapter.sample((PROCESS,), BINDING)

        self.assertEqual(wrong.error_code, "render_activity.pci_identity_changed")
        self.assertEqual(incomplete.error_code, "render_activity.fdinfo_incomplete")

    def test_non_target_descriptor_is_complete_no_client(self):
        with tempfile.TemporaryDirectory() as directory:
            adapter = self.fixture(
                Path(directory),
                info=fdinfo(gfx=100),
                target="/dev/dri/renderD128",
            )
            result = adapter.sample((PROCESS,), BINDING)

        self.assertTrue(result.complete)
        self.assertEqual(result.clients, ())

    def test_pid_reuse_during_scan_is_unknown(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            adapter = self.fixture(root, info=fdinfo(gfx=100))

            def change_identity(fd_directory):
                (root / "101" / "stat").write_text(
                    stat_line(501), encoding="utf-8"
                )
                return tuple(fd_directory.iterdir())

            adapter = ProcfsDrmEngineCounterAdapter(
                proc_root=root,
                descriptor_reader=change_identity,
                fd_target_reader=lambda path: "/dev/dri/renderD131",
            )
            result = adapter.sample((PROCESS,), BINDING)

        self.assertFalse(result.complete)
        self.assertEqual(
            result.error_code, "render_activity.process_identity_changed"
        )


def runtime(*, generation="a" * 64, sample="b" * 64):
    return ActiveGameRuntimeObservation(
        "1234",
        IDENTITY.scopes,
        (PROCESS,),
        GameRuntimeKind.NATIVE,
        generation,
        sample,
        True,
    )


def snapshot():
    value = json.loads((FIXTURES / "tv-docked.json").read_text(encoding="utf-8"))
    return dataclasses.replace(
        snapshot_from_dict(value), game_state=GameState.RUNNING
    )


def counter(value: int):
    return DrmEngineCounterSample(
        (DrmEngineClientCounters(101, 500, 7, (("gfx", value),)),),
        True,
    )


class RuntimePort:
    def __init__(self, *values):
        self.values = list(values)

    def observe(self, identity, *, user_uid):
        return self.values.pop(0)


class SnapshotPort:
    def __init__(self, value):
        self.value = value

    def observe(self):
        return VersionedObservation("snapshot", self.value, "sample")


class BindingPort:
    def __init__(self, value=BINDING):
        self.value = value

    def resolve(self, value):
        return self.value


class CounterPort:
    def __init__(self, *values):
        self.values = list(values)

    def sample(self, processes, binding):
        return self.values.pop(0)


class Waiter:
    def __init__(self):
        self.waits = []

    def wait_ms(self, value):
        self.waits.append(value)


def service(first, second, *, before=None, after=None, binding=BINDING):
    waiter = Waiter()
    value = GameRenderActivityEvidenceService(
        runtime=RuntimePort(
            before or runtime(sample="b" * 64),
            after or runtime(sample="c" * 64),
        ),
        snapshots=SnapshotPort(snapshot()),
        bindings=BindingPort(binding),
        counters=CounterPort(first, second),
        waiter=waiter,
        sample_interval_ms=250,
    )
    return value, waiter


class GameRenderActivityServiceTests(unittest.TestCase):
    def test_increasing_counter_proves_bounded_active_rendering(self):
        value, waiter = service(counter(100), counter(125))
        result = value.observe(IDENTITY, user_uid=1000)

        self.assertEqual(result.status, GameRenderActivityStatus.ACTIVE)
        self.assertEqual(result.active_engine_count, 1)
        self.assertTrue(result.proves_active_rendering)
        self.assertEqual(waiter.waits, [250])

    def test_unchanged_counter_and_no_client_are_not_active_proof(self):
        idle, _ = service(counter(100), counter(100))
        idle_result = idle.observe(IDENTITY, user_uid=1000)
        empty = DrmEngineCounterSample((), True)
        absent, _ = service(empty, empty)
        absent_result = absent.observe(IDENTITY, user_uid=1000)

        self.assertEqual(idle_result.status, GameRenderActivityStatus.IDLE_WINDOW)
        self.assertEqual(absent_result.status, GameRenderActivityStatus.NO_CLIENT)
        self.assertFalse(idle_result.proves_active_rendering)
        self.assertFalse(absent_result.proves_active_rendering)

    def test_client_change_counter_decrease_and_runtime_change_are_unknown(self):
        empty = DrmEngineCounterSample((), True)
        changed_clients, _ = service(counter(100), empty)
        decreased, _ = service(counter(100), counter(90))
        changed_runtime, _ = service(
            counter(100),
            counter(125),
            after=runtime(generation="d" * 64, sample="c" * 64),
        )

        results = (
            changed_clients.observe(IDENTITY, user_uid=1000),
            decreased.observe(IDENTITY, user_uid=1000),
            changed_runtime.observe(IDENTITY, user_uid=1000),
        )
        self.assertEqual(
            [result.reason_code for result in results],
            [
                "render_activity.client_set_changed",
                "render_activity.counter_decreased",
                "render_activity.runtime_changed",
            ],
        )
        self.assertTrue(
            all(result.status is GameRenderActivityStatus.UNKNOWN for result in results)
        )

    def test_binding_identity_must_match_exact_profile(self):
        other = DrmRenderBinding(
            "other-gpu", "0000:08:00.0", "/dev/dri/renderD131"
        )
        value, _ = service(counter(100), counter(125), binding=other)
        result = value.observe(IDENTITY, user_uid=1000)

        self.assertEqual(result.status, GameRenderActivityStatus.UNKNOWN)
        self.assertEqual(result.reason_code, "render_activity.binding_unverified")


if __name__ == "__main__":
    unittest.main()
