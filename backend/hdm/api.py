"""Delivery-neutral read-only diagnostics API."""

from __future__ import annotations

from .adapters.steamos.discovery import SteamOsDiscovery
from .application.snapshot import SnapshotService, report_to_dict
from .ports.discovery import DiscoveryPort


class DiagnosticsApi:
    def __init__(self, discovery: DiscoveryPort | None = None) -> None:
        self._service = SnapshotService(discovery or SteamOsDiscovery())

    def get_snapshot(self) -> dict[str, object]:
        """Return the versioned, privacy-safe diagnostic payload."""
        return report_to_dict(self._service.observe())
