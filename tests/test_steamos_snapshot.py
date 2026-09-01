from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from hdm.adapters.steamos.discovery import SteamOsDiscovery  # noqa: E402
from hdm.adapters.steamos.drm import DrmCardRecord, DrmConnectorRecord  # noqa: E402
from hdm.adapters.steamos.egpu_clients import EgpuClientScan  # noqa: E402
from hdm.adapters.steamos.game_scopes import GameScopeScan  # noqa: E402
from hdm.adapters.steamos.gamescope import GamescopeProcessRecord, GamescopeScan  # noqa: E402
from hdm.adapters.steamos.host import HostRecord  # noqa: E402
from hdm.adapters.steamos.pci import PciDeviceRecord, Usb4DeviceRecord  # noqa: E402
from hdm.adapters.steamos.sleep_inhibitor import InhibitorLeaseStatus  # noqa: E402
from hdm.application.snapshot import (  # noqa: E402
    SnapshotService,
    report_to_dict,
    report_to_public_dict,
)
from hdm.api import DiagnosticsApi  # noqa: E402
from hdm.domain.models import GameState, OperatingMode, SupportTier  # noqa: E402
from hdm.domain.serialization import snapshot_from_dict  # noqa: E402


class Fixed:
    def __init__(self, value):
        self.value = value

    def scan(self, *args, **kwargs):
        return self.value


class FixedTopology:
    def __init__(self, pci, usb4):
        self.pci = pci
        self.usb4 = usb4

    def scan_pci(self):
        return self.pci

    def scan_usb4(self):
        return self.usb4


class TickingMonotonic:
    def __init__(self):
        self.value = 0

    def __call__(self):
        self.value += 1_000_000
        return self.value


def certified_topology():
    root = "0000:04:00.0"
    ancestry = ("0000:00:03.1", root)
    records = (
        PciDeviceRecord(root, "0x8086", "0x15ef", "0x060400", "pcieport", ancestry, True),
        PciDeviceRecord(
            "0000:08:00.0",
            "0x1002",
            "0x7480",
            "0x030000",
            "amdgpu",
            (*ancestry, "0000:08:00.0"),
        ),
        PciDeviceRecord(
            "0000:08:00.1",
            "0x1002",
            "0xab30",
            "0x040300",
            "snd_hda_intel",
            (*ancestry, "0000:08:00.1"),
        ),
        PciDeviceRecord(
            "0000:09:00.0",
            "0x8086",
            "0x15f0",
            "0x0c0330",
            "xhci_hcd",
            (*ancestry, "0000:09:00.0"),
        ),
    )
    return records, (Usb4DeviceRecord("0-1", "Intel", "Tapex Creek", True, "c" * 64),)


class SteamOsSnapshotTests(unittest.TestCase):
    def test_aggregates_portable_state_when_no_gpu_selector_is_present(self):
        internal = DrmCardRecord(
            "card4",
            "0000:01:00.0",
            "0x1002",
            "0x0001",
            True,
            "amdgpu",
            (DrmConnectorRecord("card4", "eDP-1", "connected", "enabled", (), "d" * 64),),
        )
        process = GamescopeProcessRecord(
            50436,
            ("/usr/bin/gamescope", "-e", "-O", "*,eDP-1"),
            ("*", "eDP-1"),
            "",
            "",
            True,
        )
        discovery = SteamOsDiscovery(
            drm=Fixed((internal,)),
            gamescope=Fixed(GamescopeScan(process, 1)),
            game_scopes=Fixed(GameScopeScan(GameState.IDLE)),
            pci_usb4=FixedTopology((), ()),
            host=Fixed(HostRecord("ASUSTeK COMPUTER INC.", "ROG Ally X RC72LA", "RC72LA")),
            clock=lambda: datetime(2026, 8, 31, tzinfo=timezone.utc),
        )

        report = SnapshotService(discovery).observe()

        self.assertEqual(report.inference.mode, OperatingMode.PORTABLE)
        self.assertEqual(report.snapshot.support_tier, SupportTier.CERTIFIED)
        self.assertEqual(report.snapshot.gamescope.render_gpu_stable_id, "internal-gpu")
        self.assertEqual(report.snapshot.blockers, ())

    def test_aggregates_certified_tv_docked_state(self):
        internal = DrmCardRecord(
            "card0",
            "0000:01:00.0",
            "0x1002",
            "0x0001",
            True,
            "amdgpu",
            (DrmConnectorRecord("card0", "eDP-1", "connected", "enabled", (), "d" * 64),),
        )
        external = DrmCardRecord(
            "card9",
            "0000:08:00.0",
            "0x1002",
            "0x7480",
            False,
            "amdgpu",
            (DrmConnectorRecord("card9", "HDMI-A-9", "connected", "enabled", (), "e" * 64),),
        )
        process = GamescopeProcessRecord(
            47959,
            ("/usr/bin/gamescope", "-O", "HDMI-A-9", "--prefer-vk-device", "1002:7480"),
            ("HDMI-A-9",),
            "1002:7480",
            "1002:7480",
            True,
        )
        pci, usb4 = certified_topology()
        monotonic = TickingMonotonic()
        discovery = SteamOsDiscovery(
            drm=Fixed((internal, external)),
            gamescope=Fixed(GamescopeScan(process, 1)),
            game_scopes=Fixed(GameScopeScan(GameState.IDLE)),
            pci_usb4=FixedTopology(pci, usb4),
            host=Fixed(HostRecord("ASUSTeK COMPUTER INC.", "ROG Ally X RC72LA", "RC72LA")),
            egpu_clients=Fixed(EgpuClientScan(True, True)),
            sleep_guard_status=lambda: InhibitorLeaseStatus(True),
            clock=lambda: datetime(2026, 8, 31, tzinfo=timezone.utc),
            monotonic_ns=monotonic,
        )

        report = SnapshotService(discovery).observe()

        self.assertEqual(report.inference.mode, OperatingMode.TV_DOCKED)
        self.assertEqual(report.snapshot.support_tier, SupportTier.CERTIFIED)
        self.assertEqual(report.snapshot.blockers, ())
        self.assertTrue(report.snapshot.disconnect_readiness.ready)
        self.assertEqual(report.snapshot.schema_version, 3)
        self.assertTrue(report.snapshot.sleep_guard.active)
        payload = report_to_dict(report)
        self.assertEqual(payload["inference"]["mode"], "tv_docked")
        self.assertEqual(payload["diagnostics"]["schema_version"], 2)
        self.assertEqual(
            payload["diagnostics"]["hardware_profiles"]["host"]["status"],
            "exact",
        )
        self.assertEqual(
            payload["diagnostics"]["hardware_profiles"]["egpu"]["status"],
            "exact",
        )
        self.assertEqual(
            [row["stage"] for row in payload["diagnostics"]["timings_ms"]],
            [
                "drm",
                "gamescope",
                "game_state",
                "pci",
                "usb4",
                "host",
                "egpu_identity",
                "egpu_link",
                "disconnect_clients",
                "snapshot_total",
            ],
        )
        self.assertTrue(
            all(
                row["duration_ms"] >= 0
                for row in payload["diagnostics"]["timings_ms"]
            )
        )
        self.assertEqual(snapshot_from_dict(payload["snapshot"]), report.snapshot)
        self.assertEqual(
            DiagnosticsApi(discovery).get_snapshot(), report_to_public_dict(report)
        )

    def test_unknown_game_state_and_incomplete_g1_are_blocked(self):
        card = DrmCardRecord("card9", "0000:08:00.0", "0x1002", "0x7480", False, "amdgpu")
        process = GamescopeProcessRecord(
            10,
            ("gamescope",),
            (),
            "1002:7480",
            "1002:7480",
            True,
        )
        discovery = SteamOsDiscovery(
            drm=Fixed((card,)),
            gamescope=Fixed(GamescopeScan(process, 1)),
            game_scopes=Fixed(GameScopeScan(GameState.UNKNOWN, error="query failed")),
            pci_usb4=FixedTopology((), ()),
            host=Fixed(HostRecord("Unknown", "Unknown", "Unknown")),
            clock=lambda: datetime(2026, 8, 31, tzinfo=timezone.utc),
        )

        snapshot = discovery.collect_snapshot()
        codes = {blocker.code for blocker in snapshot.blockers}

        self.assertIn("game_state_unknown", codes)
        self.assertIn("egpu_identity_unverified", codes)
        self.assertIn("active_display_unknown", codes)
        self.assertEqual(snapshot.support_tier, SupportTier.UNKNOWN)

    def test_conflicting_process_and_environment_gpu_selectors_fail_closed(self):
        internal = DrmCardRecord(
            "card0", "0000:01:00.0", "0x1002", "0x0001", True, "amdgpu"
        )
        external = DrmCardRecord(
            "card9", "0000:08:00.0", "0x1002", "0x7480", False, "amdgpu"
        )
        process = GamescopeProcessRecord(
            20,
            ("gamescope", "--prefer-vk-device", "1002:7480"),
            ("eDP-1",),
            "1002:7480",
            "1002:0001",
            True,
        )
        discovery = SteamOsDiscovery(
            drm=Fixed((internal, external)),
            gamescope=Fixed(GamescopeScan(process, 1)),
            game_scopes=Fixed(GameScopeScan(GameState.IDLE)),
            pci_usb4=FixedTopology((), ()),
            host=Fixed(HostRecord("ASUSTeK COMPUTER INC.", "ROG Ally X RC72LA", "RC72LA")),
            clock=lambda: datetime(2026, 8, 31, tzinfo=timezone.utc),
        )

        snapshot = discovery.collect_snapshot()

        self.assertFalse(any(gpu.selected_for_render is True for gpu in snapshot.gpus))
        codes = {blocker.code for blocker in snapshot.blockers}
        self.assertIn("render_gpu_unknown", codes)
        self.assertIn("render_selector_conflict", codes)

    def test_unreadable_gamescope_environment_is_an_explicit_blocker(self):
        internal = DrmCardRecord(
            "card0",
            "0000:01:00.0",
            "0x1002",
            "0x0001",
            True,
            "amdgpu",
            (DrmConnectorRecord("card0", "eDP-1", "connected", "enabled"),),
        )
        process = GamescopeProcessRecord(
            30,
            ("gamescope", "-e", "-O", "*,eDP-1"),
            ("*", "eDP-1"),
            "",
            "",
            False,
        )
        discovery = SteamOsDiscovery(
            drm=Fixed((internal,)),
            gamescope=Fixed(GamescopeScan(process, 1)),
            game_scopes=Fixed(GameScopeScan(GameState.IDLE)),
            pci_usb4=FixedTopology((), ()),
            host=Fixed(HostRecord("ASUSTeK COMPUTER INC.", "ROG Ally X RC72LA", "RC72LA")),
            clock=lambda: datetime(2026, 8, 31, tzinfo=timezone.utc),
        )

        snapshot = discovery.collect_snapshot()

        self.assertIn(
            "gamescope_environment_unreadable",
            {blocker.code for blocker in snapshot.blockers},
        )

    def test_similar_host_name_never_receives_ally_capabilities(self):
        internal = DrmCardRecord(
            "card0",
            "0000:01:00.0",
            "0x1002",
            "0x0001",
            True,
            "amdgpu",
            (DrmConnectorRecord("card0", "eDP-1", "connected", "enabled"),),
        )
        process = GamescopeProcessRecord(
            40,
            ("gamescope", "-e", "-O", "*,eDP-1"),
            ("*", "eDP-1"),
            "",
            "",
            True,
        )
        discovery = SteamOsDiscovery(
            drm=Fixed((internal,)),
            gamescope=Fixed(GamescopeScan(process, 1)),
            game_scopes=Fixed(GameScopeScan(GameState.IDLE)),
            pci_usb4=FixedTopology((), ()),
            host=Fixed(HostRecord("ASUS Compatible", "ROG Ally X Pro RC72LA", "RC72LA")),
            clock=lambda: datetime(2026, 8, 31, tzinfo=timezone.utc),
        )

        report = SnapshotService(discovery).observe()
        payload = report_to_public_dict(report)
        profiles = payload["diagnostics"]["hardware_profiles"]
        capabilities = {item["axis"]: item for item in profiles["capabilities"]}

        self.assertEqual(report.snapshot.host_profile, "unknown")
        self.assertEqual(report.snapshot.support_tier, SupportTier.UNKNOWN)
        self.assertIn(
            "host_profile_unknown",
            {blocker.code for blocker in report.snapshot.blockers},
        )
        self.assertEqual(profiles["host"]["status"], "unknown")
        self.assertEqual(capabilities["egpu_transport"]["value"], "unknown")
        self.assertEqual(capabilities["display_handoff"]["value"], "unknown")


if __name__ == "__main__":
    unittest.main()
