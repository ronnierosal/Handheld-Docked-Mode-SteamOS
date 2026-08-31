"""Read-only snapshot orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from ..domain.inference import infer_operating_mode
from ..domain.models import ModeInference, ObservedSnapshot
from ..domain.serialization import snapshot_to_dict
from ..ports.discovery import DiscoveryPort


@dataclass(frozen=True, slots=True)
class SnapshotReport:
    snapshot: ObservedSnapshot
    inference: ModeInference


class SnapshotService:
    def __init__(self, discovery: DiscoveryPort) -> None:
        self._discovery = discovery

    def observe(self) -> SnapshotReport:
        snapshot = self._discovery.collect_snapshot()
        return SnapshotReport(snapshot, infer_operating_mode(snapshot))


def report_to_dict(report: SnapshotReport) -> dict[str, object]:
    return {
        "snapshot": snapshot_to_dict(report.snapshot),
        "inference": {
            "mode": report.inference.mode.value,
            "reasons": list(report.inference.reasons),
        },
    }
