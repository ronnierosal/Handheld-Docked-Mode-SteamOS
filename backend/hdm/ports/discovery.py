"""Read-only discovery boundary."""

from __future__ import annotations

from typing import Protocol

from ..domain.models import ObservedSnapshot


class DiscoveryPort(Protocol):
    def collect_snapshot(self) -> ObservedSnapshot:
        """Return one internally consistent observation snapshot."""
