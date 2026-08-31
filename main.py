"""Root Decky delivery adapter for the read-only HDM diagnostics API."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import decky


PLUGIN_ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = PLUGIN_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from hdm.api import DiagnosticsApi  # noqa: E402
from hdm.adapters.steamos.discovery import SteamOsDiscovery  # noqa: E402
from hdm.adapters.steamos.sleep_inhibitor import (  # noqa: E402
    G1SleepGuardHardwareDiscovery,
    SleepGuardController,
)


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

    async def get_snapshot(self) -> dict[str, object]:
        """Return the existing privacy-safe, read-only diagnostics payload."""
        return await asyncio.to_thread(self._api.get_snapshot)

    async def _main(self) -> None:
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
        except Exception:
            decky.logger.exception("HDM initial read-only snapshot failed")
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
            self._last_sleep_guard_log = current

    async def _sleep_guard_loop(self) -> None:
        while True:
            try:
                await self._reconcile_sleep_guard()
            except Exception:
                decky.logger.exception("HDM sleep guard reconciliation failed")
            await asyncio.sleep(1)

    async def _unload(self) -> None:
        if self._sleep_guard_task is not None:
            self._sleep_guard_task.cancel()
            try:
                await self._sleep_guard_task
            except asyncio.CancelledError:
                pass
            self._sleep_guard_task = None
        status = await asyncio.to_thread(self._sleep_guard.close)
        decky.logger.info("HDM sleep guard released: active=%s", status.active)
