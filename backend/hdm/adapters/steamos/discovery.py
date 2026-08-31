"""Aggregate independent SteamOS observations into one HDM snapshot."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

from ...domain.models import (
    Blocker,
    Confidence,
    DisplayKind,
    DisplayObservation,
    Evidence,
    GameState,
    GamescopeObservation,
    GpuObservation,
    GpuRole,
    ObservedSnapshot,
    SupportTier,
)
from ...profiles.ally_x import PROFILE_ID as ALLY_X_PROFILE_ID
from ...profiles.ally_x import matches_ally_x
from ...profiles.gpd_g1 import GpdG1Match, match_gpd_g1
from .drm import DrmCardRecord, DrmConnectorRecord, DrmDiscovery
from .game_scopes import GameScopeScan, SystemdGameScopeDiscovery
from .gamescope import GamescopeDiscovery, GamescopeScan
from .host import HostDiscovery, HostRecord
from .pci import PciDeviceRecord, PciUsb4Discovery, Usb4DeviceRecord


def _default_clock() -> datetime:
    return datetime.now(timezone.utc)


def _card_stable_id(card: DrmCardRecord, g1: GpdG1Match, index: int) -> str:
    if g1.verified and card.pci_bdf == g1.gpu_bdf:
        return g1.stable_id
    if card.boot_vga is True:
        return "internal-gpu"
    identity = card.vendor_device or "unknown"
    return f"observed-gpu:{identity}:{index}"


def _gpu_role(card: DrmCardRecord, g1: GpdG1Match) -> GpuRole:
    if card.boot_vga is True:
        return GpuRole.INTERNAL
    if g1.verified and card.pci_bdf == g1.gpu_bdf:
        return GpuRole.EXTERNAL
    return GpuRole.UNKNOWN


def _display_stable_id(connector: DrmConnectorRecord) -> str:
    if connector.edid_sha256:
        return f"display:{connector.edid_sha256[:16]}"
    if connector.internal:
        return "internal-panel"
    return f"observed-display:{connector.card}:{connector.name}"


class SteamOsDiscovery:
    """Concrete read-only DiscoveryPort for the current SteamOS host."""

    def __init__(
        self,
        drm: DrmDiscovery | None = None,
        gamescope: GamescopeDiscovery | None = None,
        game_scopes: SystemdGameScopeDiscovery | None = None,
        pci_usb4: PciUsb4Discovery | None = None,
        host: HostDiscovery | None = None,
        clock: Callable[[], datetime] = _default_clock,
    ) -> None:
        self._drm = drm or DrmDiscovery()
        self._gamescope = gamescope or GamescopeDiscovery()
        self._game_scopes = game_scopes or SystemdGameScopeDiscovery()
        self._pci_usb4 = pci_usb4 or PciUsb4Discovery()
        self._host = host or HostDiscovery()
        self._clock = clock

    def collect_snapshot(self) -> ObservedSnapshot:
        cards = self._drm.scan()
        gamescope_scan = self._gamescope.scan()
        gamescope_uid = (
            gamescope_scan.process.uid if gamescope_scan.process is not None else None
        )
        game_scan = self._game_scopes.scan(user_uid=gamescope_uid)
        pci_devices = self._pci_usb4.scan_pci()
        usb4_devices = self._pci_usb4.scan_usb4()
        host = self._host.scan()
        g1 = match_gpd_g1(cards, pci_devices, usb4_devices)

        gpu_rows = self._build_gpus(cards, gamescope_scan, g1)
        display_rows = self._build_displays(cards, gamescope_scan)
        gamescope = self._build_gamescope(gamescope_scan, gpu_rows)
        blockers = self._blockers(
            host,
            cards,
            gamescope_scan,
            game_scan,
            g1,
            gpu_rows,
            display_rows,
        )
        host_profile = ALLY_X_PROFILE_ID if matches_ally_x(host) else "unknown"
        support_tier = self._support_tier(host_profile, cards, g1)
        observed_at = self._clock().astimezone(timezone.utc).isoformat()
        return ObservedSnapshot(
            schema_version=1,
            observed_at=observed_at,
            host_profile=host_profile,
            support_tier=support_tier,
            game_state=game_scan.state,
            gpus=gpu_rows,
            displays=display_rows,
            gamescope=gamescope,
            blockers=blockers,
        )

    @staticmethod
    def _support_tier(
        host_profile: str,
        cards: tuple[DrmCardRecord, ...],
        g1: GpdG1Match,
    ) -> SupportTier:
        if host_profile != ALLY_X_PROFILE_ID:
            return SupportTier.UNKNOWN
        non_boot_cards = [card for card in cards if card.boot_vga is not True]
        if not non_boot_cards:
            return SupportTier.CERTIFIED
        if g1.verified and len(non_boot_cards) == 1:
            return SupportTier.CERTIFIED
        return SupportTier.UNSUPPORTED

    @staticmethod
    def _build_gpus(
        cards: tuple[DrmCardRecord, ...],
        gamescope_scan: GamescopeScan,
        g1: GpdG1Match,
    ) -> tuple[GpuObservation, ...]:
        identities = [(_card_stable_id(card, g1, index), card) for index, card in enumerate(cards)]
        selected_id = ""
        process = gamescope_scan.process if gamescope_scan.ok else None
        selectors = {
            selector
            for selector in (
                process.prefer_vk_device if process else "",
                process.mesa_vk_device_select if process else "",
            )
            if selector
        }
        if process and process.environment_readable and len(selectors) == 1:
            selector = next(iter(selectors))
            matches = [
                stable_id
                for stable_id, card in identities
                if card.vendor_device == selector
            ]
            if len(matches) == 1:
                selected_id = matches[0]
        elif process and process.environment_readable and not selectors:
            internal = [stable_id for stable_id, card in identities if card.boot_vga is True]
            if len(internal) == 1:
                selected_id = internal[0]

        rows: list[GpuObservation] = []
        for stable_id, card in identities:
            role = _gpu_role(card, g1)
            confidence = (
                Confidence.VERIFIED
                if role is not GpuRole.UNKNOWN and bool(card.vendor) and bool(card.device)
                else Confidence.OBSERVED
            )
            rows.append(
                GpuObservation(
                    stable_id=stable_id,
                    role=role,
                    vendor_device=card.vendor_device,
                    present=True,
                    selected_for_render=(stable_id == selected_id) if selected_id else None,
                    confidence=confidence,
                    evidence=(
                        Evidence("drm-sysfs", Confidence.OBSERVED, "GPU is present in DRM"),
                        Evidence(
                            "hardware-profile",
                            confidence,
                            "GPU role was classified without enumeration-order identity",
                        ),
                    ),
                )
            )
        return tuple(rows)

    @staticmethod
    def _build_displays(
        cards: tuple[DrmCardRecord, ...], gamescope_scan: GamescopeScan
    ) -> tuple[DisplayObservation, ...]:
        connectors = tuple(connector for card in cards for connector in card.connectors)
        active_connector: DrmConnectorRecord | None = None
        if gamescope_scan.ok and gamescope_scan.process:
            requested = tuple(
                name for name in gamescope_scan.process.output_order if name != "*"
            )
            matches = [
                connector
                for connector in connectors
                if connector.name in requested and connector.connected is True
            ]
            if len(matches) == 1:
                active_connector = matches[0]

        rows: list[DisplayObservation] = []
        for connector in connectors:
            status_known = connector.connected is not None
            active = (
                connector is active_connector
                if active_connector is not None
                else None
            )
            confidence = Confidence.VERIFIED if status_known else Confidence.UNKNOWN
            rows.append(
                DisplayObservation(
                    stable_id=_display_stable_id(connector),
                    kind=(
                        DisplayKind.INTERNAL if connector.internal else DisplayKind.EXTERNAL
                    ),
                    connector=connector.name,
                    connected=connector.connected,
                    active=active,
                    edid_ready=bool(connector.edid_sha256),
                    confidence=confidence,
                    evidence=(
                        Evidence("drm-sysfs", confidence, "Connector state was observed"),
                        Evidence(
                            "gamescope-process",
                            Confidence.VERIFIED if active is not None else Confidence.UNKNOWN,
                            "Active output is derived from the unique live output preference",
                        ),
                    ),
                )
            )
        return tuple(rows)

    @staticmethod
    def _build_gamescope(
        scan: GamescopeScan, gpus: tuple[GpuObservation, ...]
    ) -> GamescopeObservation:
        if not scan.ok or scan.process is None:
            running = True if scan.candidate_count > 0 else (
                False if scan.error == "Gamescope process was not found" else None
            )
            return GamescopeObservation(
                running=running,
                pid=None,
                confidence=Confidence.UNKNOWN,
                evidence=(Evidence("procfs", Confidence.UNKNOWN, scan.error),),
            )
        selected = [gpu for gpu in gpus if gpu.selected_for_render is True]
        render_id = selected[0].stable_id if len(selected) == 1 else ""
        render_vendor = selected[0].vendor_device if len(selected) == 1 else ""
        verified = (
            len(selected) == 1
            and selected[0].confidence is Confidence.VERIFIED
            and bool(scan.process.output_order)
            and scan.process.environment_readable
        )
        confidence = Confidence.VERIFIED if verified else Confidence.OBSERVED
        return GamescopeObservation(
            running=True,
            pid=scan.process.pid,
            output_order=scan.process.output_order,
            render_gpu_stable_id=render_id,
            render_vendor_device=render_vendor,
            confidence=confidence,
            evidence=(
                Evidence(
                    "procfs",
                    confidence,
                    "Unique Gamescope process and startup arguments were observed",
                ),
            ),
        )

    @staticmethod
    def _blockers(
        host: HostRecord,
        cards: tuple[DrmCardRecord, ...],
        gamescope: GamescopeScan,
        games: GameScopeScan,
        g1: GpdG1Match,
        gpus: tuple[GpuObservation, ...],
        displays: tuple[DisplayObservation, ...],
    ) -> tuple[Blocker, ...]:
        blockers: list[Blocker] = []
        if not matches_ally_x(host):
            blockers.append(
                Blocker("host_profile_unknown", "Host is not a certified Ally X profile.")
            )
        if not cards:
            blockers.append(
                Blocker("drm_inventory_unavailable", "No DRM GPU inventory was observed.")
            )
        if not gamescope.ok:
            blockers.append(Blocker("gamescope_unverified", gamescope.error))
        elif gamescope.process and not gamescope.process.environment_readable:
            blockers.append(
                Blocker(
                    "gamescope_environment_unreadable",
                    "Gamescope GPU-selector environment is not readable at this privilege level.",
                )
            )
        elif gamescope.process:
            selectors = {
                selector
                for selector in (
                    gamescope.process.prefer_vk_device,
                    gamescope.process.mesa_vk_device_select,
                )
                if selector
            }
            if len(selectors) > 1:
                blockers.append(
                    Blocker(
                        "render_selector_conflict",
                        "Gamescope argument and environment GPU selectors conflict.",
                    )
                )
        if games.state is GameState.UNKNOWN:
            blockers.append(Blocker("game_state_unknown", games.error))
        if g1.detected and not g1.verified:
            blockers.append(Blocker("egpu_identity_unverified", g1.reason))
        if len([gpu for gpu in gpus if gpu.selected_for_render is True]) != 1:
            blockers.append(Blocker("render_gpu_unknown", "Active render GPU is not verified."))
        if len([display for display in displays if display.active is True]) != 1:
            blockers.append(Blocker("active_display_unknown", "Active display is not verified."))
        return tuple(blockers)
