"""Internal approval policy for future guarded eGPU process release.

This module issues and validates backend-owned approval tokens.  It contains no
signal mechanism and is not exposed by the Decky delivery adapter.
"""

from __future__ import annotations

import hashlib
import re
import secrets
import threading
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Callable

from ..domain.models import (
    EgpuClientKind,
    EgpuClientObservation,
    EgpuResourceKind,
    ObservedSnapshot,
)


TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{16,96}$")
DEFAULT_APPROVAL_TTL_SECONDS = 120.0
MAX_APPROVAL_TOKENS = 3
MAX_RELEASE_TARGETS = 32


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
class ProcessReleaseApproval:
    phase: ReleasePhase
    egpu_stable_id: str
    observed_generation: str
    client_fingerprint: str
    targets: tuple[ProcessReleaseTarget, ...]
    prior_graceful_operation_id: str = ""


@dataclass(frozen=True, slots=True)
class GracefulReleaseEvidence:
    operation_id: str
    attempted_instance_ids: tuple[str, ...]
    observed_generation: str

    def __post_init__(self) -> None:
        if not TOKEN_RE.fullmatch(self.operation_id):
            raise ValueError("graceful release operation ID is invalid")
        if not self.attempted_instance_ids or not self.observed_generation:
            raise ValueError("graceful release evidence is incomplete")


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


def _client_fingerprint(clients: tuple[EgpuClientObservation, ...]) -> str:
    rows = sorted(
        (
            client.instance_id,
            str(client.pid),
            client.name,
            client.kind.value,
            "1" if client.close_eligible else "0",
            ",".join(sorted(resource.value for resource in client.resources)),
        )
        for client in clients
    )
    encoded = "\n".join("|".join(row) for row in rows).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _eligible_targets(
    clients: tuple[EgpuClientObservation, ...],
) -> tuple[ProcessReleaseTarget, ...]:
    eligible = tuple(
        ProcessReleaseTarget(
            instance_id=client.instance_id,
            pid=client.pid,
            name=client.name,
            resources=client.resources,
        )
        for client in clients
        if client.kind is EgpuClientKind.USER and client.close_eligible
    )
    if len(eligible) > MAX_RELEASE_TARGETS:
        raise ValueError("eligible process target count exceeds the approval bound")
    return eligible


class ProcessReleaseApprovalStore:
    def __init__(
        self,
        *,
        ttl_seconds: float = DEFAULT_APPROVAL_TTL_SECONDS,
        max_tokens: int = MAX_APPROVAL_TOKENS,
        monotonic: Callable[[], float] = time.monotonic,
        token_factory: Callable[[], str] | None = None,
    ) -> None:
        if ttl_seconds <= 0 or ttl_seconds > 300:
            raise ValueError("process approval TTL must be between 0 and 300 seconds")
        if max_tokens <= 0 or max_tokens > 10:
            raise ValueError("process approval token bound must be between 1 and 10")
        self._ttl_seconds = ttl_seconds
        self._max_tokens = max_tokens
        self._monotonic = monotonic
        self._token_factory = token_factory or (lambda: secrets.token_urlsafe(18))
        self._values: dict[str, tuple[float, ProcessReleaseApproval]] = {}
        self._lock = threading.Lock()

    def issue(
        self,
        snapshot: ObservedSnapshot,
        *,
        observed_generation: str,
        phase: ReleasePhase,
        graceful_evidence: GracefulReleaseEvidence | None = None,
    ) -> ProcessReleasePreview:
        readiness = snapshot.disconnect_readiness
        if not observed_generation:
            raise ValueError("process approval observation generation is required")
        if not readiness.applicable or not readiness.egpu_stable_id:
            raise ValueError("an exact eGPU identity is required")
        if not readiness.scan_complete:
            raise ValueError("eGPU client scan must be complete")
        if readiness.storage_in_use:
            raise ValueError("eGPU storage use is non-overridable")
        targets = _eligible_targets(readiness.clients)
        if not targets:
            raise ValueError("no close-eligible eGPU user process was observed")
        prior_graceful_operation_id = ""
        if phase is ReleasePhase.FORCE:
            if graceful_evidence is None:
                raise ValueError("force approval requires a prior graceful attempt")
            if observed_generation == graceful_evidence.observed_generation:
                raise ValueError("force approval requires a post-graceful observation")
            previously_attempted = frozenset(graceful_evidence.attempted_instance_ids)
            if any(target.instance_id not in previously_attempted for target in targets):
                raise ValueError("force approval cannot add a new process target")
            prior_graceful_operation_id = graceful_evidence.operation_id
        elif graceful_evidence is not None:
            raise ValueError("graceful evidence is valid only for force approval")
        approval = ProcessReleaseApproval(
            phase=phase,
            egpu_stable_id=readiness.egpu_stable_id,
            observed_generation=observed_generation,
            client_fingerprint=_client_fingerprint(readiness.clients),
            targets=targets,
            prior_graceful_operation_id=prior_graceful_operation_id,
        )
        with self._lock:
            self._expire_locked()
            while len(self._values) >= self._max_tokens:
                oldest = min(self._values, key=lambda token: self._values[token][0])
                self._values.pop(oldest)
            token = self._token_factory()
            if not TOKEN_RE.fullmatch(token) or token in self._values:
                raise ValueError("process approval token generator returned an invalid token")
            self._values[token] = (self._monotonic(), approval)
        return ProcessReleasePreview(
            token=token,
            phase=phase,
            expires_in_seconds=max(1, int(self._ttl_seconds)),
            targets=tuple(
                ProcessReleasePreviewRow(target.name, target.resources)
                for target in targets
            ),
            protected_client_count=len(readiness.clients) - len(targets),
        )

    def consume(self, token: str) -> ProcessReleaseApproval:
        if not TOKEN_RE.fullmatch(token):
            raise ValueError("process approval token is invalid")
        with self._lock:
            self._expire_locked()
            value = self._values.pop(token, None)
            if value is None:
                raise ValueError("process approval expired or was already used")
            return value[1]

    def _expire_locked(self) -> None:
        cutoff = self._monotonic() - self._ttl_seconds
        for token in [
            token for token, (created, _) in self._values.items() if created < cutoff
        ]:
            self._values.pop(token, None)


def revalidate_process_release(
    approval: ProcessReleaseApproval,
    snapshot: ObservedSnapshot,
    *,
    observed_generation: str,
) -> tuple[ProcessReleaseTarget, ...]:
    readiness = snapshot.disconnect_readiness
    if not observed_generation or observed_generation == approval.observed_generation:
        raise ValueError("a fresh observation is required before process release")
    if not readiness.applicable or not readiness.scan_complete:
        raise ValueError("fresh eGPU client evidence is incomplete")
    if readiness.egpu_stable_id != approval.egpu_stable_id:
        raise ValueError("eGPU identity changed after approval")
    if readiness.storage_in_use:
        raise ValueError("eGPU storage use is non-overridable")
    if _client_fingerprint(readiness.clients) != approval.client_fingerprint:
        raise ValueError("eGPU client evidence changed after approval")
    current_targets = _eligible_targets(readiness.clients)
    if current_targets != approval.targets:
        raise ValueError("eligible process instances changed after approval")
    return approval.targets
