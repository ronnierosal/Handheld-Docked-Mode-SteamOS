"""Strict parsing for versioned read-only snapshot payloads."""

from __future__ import annotations

from typing import Any

from .models import (
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


def _optional_bool(value: Any, field_name: str) -> bool | None:
    if value is None or isinstance(value, bool):
        return value
    raise ValueError(f"{field_name} must be a boolean or null")


def _required_bool(value: Any, field_name: str) -> bool:
    parsed = _optional_bool(value, field_name)
    if parsed is None:
        raise ValueError(f"{field_name} must be a boolean")
    return parsed


def _optional_pid(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError("gamescope.pid must be a positive integer or null")
    return value


def _evidence(values: list[dict[str, Any]] | None) -> tuple[Evidence, ...]:
    return tuple(
        Evidence(
            source=str(value["source"]),
            confidence=Confidence(value["confidence"]),
            detail=str(value.get("detail", "")),
        )
        for value in values or []
    )


def snapshot_from_dict(value: dict[str, Any]) -> ObservedSnapshot:
    version = int(value["schema_version"])
    if version != 1:
        raise ValueError(f"Unsupported snapshot schema version: {version}")

    gpus = tuple(
        GpuObservation(
            stable_id=str(gpu["stable_id"]),
            role=GpuRole(gpu["role"]),
            vendor_device=str(gpu.get("vendor_device", "")),
            present=_required_bool(gpu["present"], "gpu.present"),
            selected_for_render=_optional_bool(
                gpu.get("selected_for_render"), "gpu.selected_for_render"
            ),
            confidence=Confidence(gpu.get("confidence", "unknown")),
            evidence=_evidence(gpu.get("evidence")),
        )
        for gpu in value["gpus"]
    )
    displays = tuple(
        DisplayObservation(
            stable_id=str(display["stable_id"]),
            kind=DisplayKind(display["kind"]),
            connector=str(display.get("connector", "")),
            connected=_optional_bool(display.get("connected"), "display.connected"),
            active=_optional_bool(display.get("active"), "display.active"),
            edid_ready=_optional_bool(display.get("edid_ready"), "display.edid_ready"),
            confidence=Confidence(display.get("confidence", "unknown")),
            evidence=_evidence(display.get("evidence")),
        )
        for display in value["displays"]
    )
    gamescope_value = value["gamescope"]
    gamescope = GamescopeObservation(
        running=_optional_bool(gamescope_value.get("running"), "gamescope.running"),
        pid=_optional_pid(gamescope_value.get("pid")),
        output_order=tuple(str(item) for item in gamescope_value.get("output_order", [])),
        render_gpu_stable_id=str(gamescope_value.get("render_gpu_stable_id", "")),
        render_vendor_device=str(gamescope_value.get("render_vendor_device", "")),
        confidence=Confidence(gamescope_value.get("confidence", "unknown")),
        evidence=_evidence(gamescope_value.get("evidence")),
    )
    blockers = tuple(
        Blocker(code=str(blocker["code"]), message=str(blocker["message"]))
        for blocker in value.get("blockers", [])
    )
    return ObservedSnapshot(
        schema_version=version,
        observed_at=str(value["observed_at"]),
        host_profile=str(value.get("host_profile", "")),
        support_tier=SupportTier(value.get("support_tier", "unknown")),
        game_state=GameState(value["game_state"]),
        gpus=gpus,
        displays=displays,
        gamescope=gamescope,
        blockers=blockers,
    )
