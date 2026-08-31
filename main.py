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


class Plugin:
    def __init__(self) -> None:
        self._api = DiagnosticsApi()

    async def get_snapshot(self) -> dict[str, object]:
        """Return the existing privacy-safe, read-only diagnostics payload."""
        return await asyncio.to_thread(self._api.get_snapshot)

    async def _main(self) -> None:
        try:
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

    async def _unload(self) -> None:
        pass
