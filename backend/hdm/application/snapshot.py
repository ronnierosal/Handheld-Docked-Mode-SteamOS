"""Read-only snapshot orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from ..domain.control_plane import WorkflowState
from ..domain.health import HealthAssessment, assess_snapshot_health
from ..domain.inference import infer_placement
from ..domain.inference import infer_operating_mode
from ..domain.models import ModeInference, ObservedSnapshot
from ..domain.peripheral_handoff import PeripheralObservation
from ..domain.serialization import snapshot_to_dict
from ..ports.discovery import DiscoveryPort, DiscoveryTiming
from ..ports.peripheral_handoff import PeripheralObservationPort
from ..profiles.registry import (
    resolve_runtime_profiles,
    runtime_profile_diagnostics_to_dict,
)


@dataclass(frozen=True, slots=True)
class SnapshotReport:
    snapshot: ObservedSnapshot
    inference: ModeInference
    health: HealthAssessment | None = None
    timings: tuple[DiscoveryTiming, ...] = field(default_factory=tuple)
    workflow: WorkflowState | None = None
    peripheral: PeripheralObservation | None = None
    workflow_unavailable: bool = False
    peripheral_unavailable: bool = False


class SnapshotService:
    def __init__(
        self,
        discovery: DiscoveryPort,
        *,
        workflow_observation: Callable[[], WorkflowState] | None = None,
        peripheral_observation: PeripheralObservationPort | None = None,
    ) -> None:
        self._discovery = discovery
        self._workflow_observation = workflow_observation
        self._peripheral_observation = peripheral_observation

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
        inference = infer_operating_mode(snapshot)
        workflow, workflow_unavailable = self._observe_workflow()
        peripheral, peripheral_unavailable = self._observe_peripheral()
        return SnapshotReport(
            snapshot=snapshot,
            inference=inference,
            health=assess_snapshot_health(
                snapshot,
                infer_placement(snapshot),
                peripheral,
                workflow,
                peripheral_unavailable=peripheral_unavailable,
                workflow_unavailable=workflow_unavailable,
            ),
            timings=timings,
            workflow=workflow,
            peripheral=peripheral,
            workflow_unavailable=workflow_unavailable,
            peripheral_unavailable=peripheral_unavailable,
        )

    def _observe_workflow(self) -> tuple[WorkflowState | None, bool]:
        if self._workflow_observation is None:
            return None, False
        try:
            value = self._workflow_observation()
        except Exception:
            return None, True
        return (value, False) if isinstance(value, WorkflowState) else (None, True)

    def _observe_peripheral(self) -> tuple[PeripheralObservation | None, bool]:
        if self._peripheral_observation is None:
            return None, False
        try:
            value = self._peripheral_observation.observe()
        except Exception:
            return None, True
        return (value, False) if isinstance(value, PeripheralObservation) else (None, True)


def report_to_dict(report: SnapshotReport) -> dict[str, object]:
    profiles = resolve_runtime_profiles(report.snapshot)
    health = report.health or assess_snapshot_health(
        report.snapshot,
        infer_placement(report.snapshot),
        report.peripheral,
        report.workflow,
        peripheral_unavailable=report.peripheral_unavailable,
        workflow_unavailable=report.workflow_unavailable,
    )
    return {
        "snapshot": snapshot_to_dict(report.snapshot),
        "inference": {
            "mode": report.inference.mode.value,
            "reasons": list(report.inference.reasons),
        },
        "health": {
            "state": health.state.value,
            "components": [
                {
                    "component": component.component.value,
                    "state": component.state.value,
                    "reason": component.reason,
                }
                for component in health.components
            ],
            "blockers": list(health.blockers),
        },
        "diagnostics": {
            "schema_version": 2,
            "timings_ms": [
                {
                    "stage": timing.stage,
                    "duration_ms": round(max(0.0, timing.duration_ms), 3),
                }
                for timing in report.timings
            ],
            "hardware_profiles": runtime_profile_diagnostics_to_dict(
                profiles.diagnostics()
            ),
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
    payload["delivery_schema_version"] = 2
    return payload
