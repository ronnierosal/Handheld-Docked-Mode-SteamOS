"""Read-only snapshot orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..domain.inference import infer_operating_mode
from ..domain.models import ModeInference, ObservedSnapshot
from ..domain.serialization import snapshot_to_dict
from ..ports.discovery import DiscoveryPort, DiscoveryTiming


@dataclass(frozen=True, slots=True)
class SnapshotReport:
    snapshot: ObservedSnapshot
    inference: ModeInference
    timings: tuple[DiscoveryTiming, ...] = field(default_factory=tuple)


class SnapshotService:
    def __init__(self, discovery: DiscoveryPort) -> None:
        self._discovery = discovery

    def observe(self) -> SnapshotReport:
        timed_collector = getattr(
            self._discovery, "collect_snapshot_with_timings", None
        )
        if callable(timed_collector):
            result = timed_collector()
            snapshot = result.snapshot
            timings = result.timings
        else:
            snapshot = self._discovery.collect_snapshot()
            timings = ()
        return SnapshotReport(snapshot, infer_operating_mode(snapshot), timings)


def report_to_dict(report: SnapshotReport) -> dict[str, object]:
    return {
        "snapshot": snapshot_to_dict(report.snapshot),
        "inference": {
            "mode": report.inference.mode.value,
            "reasons": list(report.inference.reasons),
        },
        "diagnostics": {
            "schema_version": 1,
            "timings_ms": [
                {
                    "stage": timing.stage,
                    "duration_ms": round(max(0.0, timing.duration_ms), 3),
                }
                for timing in report.timings
            ],
        },
    }
