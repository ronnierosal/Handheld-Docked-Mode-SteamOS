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


def report_to_public_dict(report: SnapshotReport) -> dict[str, object]:
    """Return only the categorical evidence required by the Decky frontend."""
    payload = report_to_dict(report)
    snapshot = payload["snapshot"]
    for gpu in snapshot["gpus"]:
        gpu.pop("stable_id", None)
        gpu.pop("vendor_device", None)
    for display in snapshot["displays"]:
        display.pop("stable_id", None)
        display.pop("connector", None)
    gamescope = snapshot["gamescope"]
    for key in (
        "pid",
        "output_order",
        "render_gpu_stable_id",
        "render_vendor_device",
    ):
        gamescope.pop(key, None)
    readiness = snapshot["disconnect_readiness"]
    readiness.pop("egpu_stable_id", None)
    for client in readiness["clients"]:
        client.pop("instance_id", None)
        client.pop("pid", None)
        client.pop("process_start_time", None)
    payload["delivery_schema_version"] = 1
    return payload
