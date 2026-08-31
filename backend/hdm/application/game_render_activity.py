"""Bounded read-only proof of game activity on one exact DRM GPU."""

from __future__ import annotations

from ..domain.game_render_activity import (
    DrmEngineCounterSample,
    GameRenderActivityEvidence,
    GameRenderActivityStatus,
)
from ..domain.game_runtime import GameRuntimeKind
from ..domain.game_session import ActiveGameIdentity
from ..domain.models import GameState
from ..ports.game_render_activity import (
    DrmEngineCounterPort,
    DrmRenderBindingPort,
)
from ..ports.game_runtime import GameRuntimeObservationPort
from ..ports.runtime_transition import DeadlineWaitPort
from ..ports.transition import TransitionObservationPort
from ..profiles.registry import resolve_runtime_profiles


MIN_SAMPLE_INTERVAL_MS = 50
MAX_SAMPLE_INTERVAL_MS = 250


class GameRenderActivityEvidenceService:
    def __init__(
        self,
        *,
        runtime: GameRuntimeObservationPort,
        snapshots: TransitionObservationPort,
        bindings: DrmRenderBindingPort,
        counters: DrmEngineCounterPort,
        waiter: DeadlineWaitPort,
        sample_interval_ms: int = 250,
    ) -> None:
        if not MIN_SAMPLE_INTERVAL_MS <= sample_interval_ms <= MAX_SAMPLE_INTERVAL_MS:
            raise ValueError("render activity sample interval is invalid")
        self._runtime = runtime
        self._snapshots = snapshots
        self._bindings = bindings
        self._counters = counters
        self._waiter = waiter
        self._sample_interval_ms = sample_interval_ms

    def observe(
        self, identity: ActiveGameIdentity, *, user_uid: int
    ) -> GameRenderActivityEvidence:
        if user_uid <= 0 or user_uid > 2_147_483_647:
            return self._unknown("render_activity.user_invalid")
        before = self._runtime_observation(identity, user_uid)
        if not self._runtime_matches(identity, before):
            return self._unknown("render_activity.runtime_unavailable")
        try:
            snapshot_observation = self._snapshots.observe()
        except Exception:
            snapshot_observation = None
        if snapshot_observation is None:
            return self._unknown("render_activity.snapshot_unavailable")
        snapshot = snapshot_observation.snapshot
        if snapshot.game_state is not GameState.RUNNING:
            return self._unknown("render_activity.game_state_changed")
        profiles = resolve_runtime_profiles(snapshot)
        readiness = snapshot.disconnect_readiness
        if (
            not profiles.exact_host
            or not profiles.exact_egpu
            or not readiness.applicable
            or not readiness.scan_complete
            or readiness.error
            or readiness.egpu_stable_id != profiles.egpu_stable_id
        ):
            return self._unknown("render_activity.egpu_unverified")
        try:
            binding = self._bindings.resolve(snapshot)
        except Exception:
            binding = None
        if binding is None or binding.gpu_stable_id != profiles.egpu_stable_id:
            return self._unknown("render_activity.binding_unverified")

        first = self._counter_sample(before.processes, binding)
        if first is None or not first.complete:
            return self._unknown("render_activity.counter_unavailable")
        try:
            self._waiter.wait_ms(self._sample_interval_ms)
        except Exception:
            return self._unknown("render_activity.wait_failed")
        second = self._counter_sample(before.processes, binding)
        if second is None or not second.complete:
            return self._unknown("render_activity.counter_unavailable")
        after = self._runtime_observation(identity, user_uid)
        if (
            not self._runtime_matches(identity, after)
            or before.generation != after.generation
            or before.sample_id == after.sample_id
        ):
            return self._unknown("render_activity.runtime_changed")
        return self._compare(first, second, after.runtime_kind)

    def _runtime_observation(self, identity, user_uid):
        try:
            return self._runtime.observe(identity, user_uid=user_uid)
        except Exception:
            return None

    @staticmethod
    def _runtime_matches(identity, observation):
        return bool(
            observation is not None
            and observation.exact
            and observation.steam_app_id == identity.steam_app_id
            and observation.scopes == identity.scopes
        )

    def _counter_sample(self, processes, binding):
        try:
            return self._counters.sample(processes, binding)
        except Exception:
            return None

    @classmethod
    def _compare(
        cls,
        first: DrmEngineCounterSample,
        second: DrmEngineCounterSample,
        runtime_kind: GameRuntimeKind,
    ) -> GameRenderActivityEvidence:
        first_clients = {client.identity: client for client in first.clients}
        second_clients = {client.identity: client for client in second.clients}
        if first_clients.keys() != second_clients.keys():
            return cls._unknown("render_activity.client_set_changed")
        if not first_clients:
            return GameRenderActivityEvidence(
                GameRenderActivityStatus.NO_CLIENT,
                runtime_kind,
                0,
                "render_activity.no_client",
            )
        active = 0
        for identity, first_client in first_clients.items():
            second_client = second_clients[identity]
            first_counters = dict(first_client.counters_ns)
            second_counters = dict(second_client.counters_ns)
            if first_counters.keys() != second_counters.keys():
                return cls._unknown("render_activity.engine_set_changed")
            for engine, first_value in first_counters.items():
                second_value = second_counters[engine]
                if second_value < first_value:
                    return cls._unknown("render_activity.counter_decreased")
                if second_value > first_value:
                    active += 1
        if active:
            return GameRenderActivityEvidence(
                GameRenderActivityStatus.ACTIVE,
                runtime_kind,
                active,
                "render_activity.active",
            )
        return GameRenderActivityEvidence(
            GameRenderActivityStatus.IDLE_WINDOW,
            runtime_kind,
            0,
            "render_activity.idle_window",
        )

    @staticmethod
    def _unknown(reason: str) -> GameRenderActivityEvidence:
        return GameRenderActivityEvidence(
            GameRenderActivityStatus.UNKNOWN,
            GameRuntimeKind.UNKNOWN,
            0,
            reason,
        )
