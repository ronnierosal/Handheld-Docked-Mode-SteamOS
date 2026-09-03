from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from hdm.adapters.steamos.audio_handoff import (  # noqa: E402
    G1AudioHandoff,
)
from hdm.adapters.steamos.commands import (  # noqa: E402
    AudioCommandResult,
    PipeWireCommandRunner,
)
from hdm.adapters.steamos.gamescope_user import GamescopeUserContext  # noqa: E402
from hdm.delivery.audio_state import PortableAudioStateStore  # noqa: E402
from hdm.domain.control_plane import PlacementState  # noqa: E402


USER = GamescopeUserContext(
    "deck",
    1000,
    1000,
    Path("/home/deck"),
    Path("/run/user/1000"),
    Path("/run/user/1000/bus"),
)
INTERNAL = "alsa_loopback_device.alsa_output.pci-0000_64_00.6.analog-stereo"
EXTERNAL = "alsa_loopback_device.alsa_output.pci-0000_08_00.1.hdmi-stereo-extra1"


class FakeCommands:
    def __init__(
        self,
        *,
        default=INTERNAL,
        configured=None,
        duplicate_external=False,
        fail_set=False,
    ):
        self.default = default
        self.configured = configured or default
        self.duplicate_external = duplicate_external
        self.fail_set = fail_set
        self.set_ids = []

    def dump(self, user):
        values = [
            self.device(50, "0000:64:00.6"),
            self.device(105, "0000:08:00.1"),
            self.sink(62, INTERNAL, 50),
            self.sink(101, EXTERNAL, 105),
            {
                "id": 41,
                "type": "PipeWire:Interface:Metadata",
                "metadata": [
                    {"key": "default.audio.sink", "value": {"name": self.default}},
                    {
                        "key": "default.configured.audio.sink",
                        "value": {"name": self.configured},
                    },
                ],
            },
        ]
        if self.duplicate_external:
            values.append(self.sink(102, EXTERNAL + "-other", 105))
        return AudioCommandResult(True, json.dumps(values).encode("utf-8"))

    def set_default(self, user, object_id):
        self.set_ids.append(object_id)
        if self.fail_set:
            return AudioCommandResult(False, code="injected")
        self.default = {62: INTERNAL, 101: EXTERNAL}.get(object_id, self.default)
        self.configured = self.default
        return AudioCommandResult(True)

    @staticmethod
    def device(object_id, bdf):
        return {
            "id": object_id,
            "type": "PipeWire:Interface:Device",
            "info": {"props": {"device.bus-path": f"pci-{bdf}"}},
        }

    @staticmethod
    def sink(object_id, name, device_id):
        return {
            "id": object_id,
            "type": "PipeWire:Interface:Node",
            "info": {
                "props": {
                    "media.class": "Audio/Sink",
                    "alsa.loopback": True,
                    "node.name": name,
                    "device.id": device_id,
                }
            },
        }


class G1AudioHandoffTests(unittest.TestCase):
    def handoff(self, root, commands):
        return G1AudioHandoff(
            commands=commands,
            state=PortableAudioStateStore(root),
            resolve_g1_audio_bdf=lambda: "0000:08:00.1",
        )

    def test_dock_selects_exact_g1_loopback_and_records_portable_sink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            commands = FakeCommands()
            result = self.handoff(root, commands).switch(
                PlacementState.DOCKED_EGPU, USER
            )

            self.assertTrue(result.succeeded)
            self.assertEqual(result.code, "audio.default_verified")
            self.assertEqual(commands.set_ids, [101])
            self.assertEqual(PortableAudioStateStore(root).load(), INTERNAL)
            self.assertTrue(result.receipt.changed)

    def test_portable_observation_records_current_sink_before_attach(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            commands = FakeCommands()
            result = self.handoff(root, commands).remember_portable(USER)

            self.assertTrue(result.succeeded)
            self.assertEqual(PortableAudioStateStore(root).load(), INTERNAL)
            self.assertEqual(commands.set_ids, [])

    def test_current_portable_default_wins_over_stale_configured_g1_sink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            commands = FakeCommands(default=INTERNAL, configured=EXTERNAL)
            result = self.handoff(root, commands).remember_portable(USER)

            self.assertTrue(result.succeeded)
            self.assertEqual(PortableAudioStateStore(root).load(), INTERNAL)

    def test_already_external_requires_a_recorded_portable_rollback(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.handoff(
                Path(directory), FakeCommands(default=EXTERNAL)
            ).switch(PlacementState.DOCKED_EGPU, USER)

            self.assertFalse(result.succeeded)
            self.assertEqual(result.code, "audio.rollback_sink_unavailable")

    def test_portable_restores_recorded_sink_and_keeps_rollback_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = PortableAudioStateStore(root)
            store.save(INTERNAL)
            commands = FakeCommands(default=EXTERNAL)
            result = self.handoff(root, commands).switch(
                PlacementState.PORTABLE, USER
            )

            self.assertTrue(result.succeeded)
            self.assertEqual(commands.set_ids, [62])
            self.assertEqual(store.load(), INTERNAL)

    def test_failed_presentation_can_rollback_the_audio_change(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            commands = FakeCommands()
            handoff = self.handoff(root, commands)
            result = handoff.switch(PlacementState.DOCKED_EGPU, USER)

            self.assertTrue(handoff.rollback(result.receipt, USER))
            self.assertEqual(commands.default, INTERNAL)
            self.assertEqual(commands.set_ids, [101, 62])
            self.assertEqual(PortableAudioStateStore(root).load(), "")

    def test_ambiguous_external_sink_fails_without_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            commands = FakeCommands(duplicate_external=True)
            result = self.handoff(Path(directory), commands).switch(
                PlacementState.DOCKED_EGPU, USER
            )

            self.assertFalse(result.succeeded)
            self.assertEqual(result.code, "audio.external_sink_ambiguous")
            self.assertEqual(commands.set_ids, [])

    def test_unverified_g1_identity_fails_without_dump_or_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            commands = FakeCommands()
            handoff = G1AudioHandoff(
                commands=commands,
                state=PortableAudioStateStore(Path(directory)),
                resolve_g1_audio_bdf=lambda: "",
            )
            result = handoff.switch(PlacementState.DOCKED_EGPU, USER)

            self.assertFalse(result.succeeded)
            self.assertEqual(result.code, "audio.g1_identity_unverified")
            self.assertEqual(commands.set_ids, [])


class PipeWireCommandRunnerTests(unittest.TestCase):
    def test_set_default_argv_is_numeric_only(self):
        calls = []

        def run(argv, **kwargs):
            calls.append(tuple(argv))
            return type(
                "Completed",
                (),
                {"returncode": 0, "stdout": b"", "stderr": b""},
            )()

        import hdm.adapters.steamos.commands as module

        original = module.subprocess.run
        module.subprocess.run = run
        try:
            runner = PipeWireCommandRunner(effective_uid=lambda: 0)
            self.assertTrue(runner.set_default(USER, 101).ok)
            self.assertFalse(runner.set_default(USER, -1).ok)
        finally:
            module.subprocess.run = original

        self.assertEqual(calls[0][-3:], ("/usr/bin/wpctl", "set-default", "101"))


if __name__ == "__main__":
    unittest.main()
