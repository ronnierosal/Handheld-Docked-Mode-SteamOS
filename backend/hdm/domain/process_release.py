"""Immutable process-release values shared by policy and future mechanisms."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .models import EgpuClientKind, EgpuResourceKind


class ReleasePhase(StrEnum):
    GRACEFUL = "graceful"
    FORCE = "force"


@dataclass(frozen=True, slots=True)
class ProcessReleaseTarget:
    instance_id: str
    pid: int
    name: str
    resources: tuple[EgpuResourceKind, ...]


@dataclass(frozen=True, slots=True)
class ProcessClientFact:
    instance_id: str
    pid: int
    name: str
    kind: EgpuClientKind
    resources: tuple[EgpuResourceKind, ...]
    close_eligible: bool


@dataclass(frozen=True, slots=True)
class ProcessReleaseApproval:
    phase: ReleasePhase
    egpu_stable_id: str
    observed_generation: str
    client_fingerprint: str
    targets: tuple[ProcessReleaseTarget, ...]
    observed_clients: tuple[ProcessClientFact, ...]
    prior_graceful_operation_id: str = ""


@dataclass(frozen=True, slots=True)
class ProcessReleasePreviewRow:
    name: str
    resources: tuple[EgpuResourceKind, ...]


@dataclass(frozen=True, slots=True)
class ProcessReleasePreview:
    token: str
    phase: ReleasePhase
    expires_in_seconds: int
    targets: tuple[ProcessReleasePreviewRow, ...]
    protected_client_count: int

