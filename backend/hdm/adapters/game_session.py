"""Exact Steam scope scan adapter for guarded game workflows."""

from __future__ import annotations

import hashlib
import threading
from typing import Protocol

from ..adapters.steamos.game_scopes import GameScopeScan
from ..domain.game_session import ActiveGameIdentity, GameSessionObservation
from ..domain.models import GameState


class GameScopeScanPort(Protocol):
    def scan(self) -> GameScopeScan: ...


class GameScopeSessionObservationAdapter:
    def __init__(self, discovery: GameScopeScanPort) -> None:
        self._discovery = discovery
        self._counter = 0
        self._lock = threading.Lock()

    def observe(self) -> GameSessionObservation:
        scan = self._discovery.scan()
        identity = None
        state = scan.state
        if scan.state is GameState.RUNNING:
            if scan.active_app_id and scan.scopes:
                try:
                    identity = ActiveGameIdentity(scan.active_app_id, scan.scopes)
                except ValueError:
                    state = GameState.UNKNOWN
            else:
                state = GameState.UNKNOWN
        semantic = "|".join(
            (
                state.value,
                identity.steam_app_id if identity is not None else "",
                *(identity.scopes if identity is not None else ()),
            )
        ).encode("utf-8")
        with self._lock:
            self._counter += 1
            counter = self._counter
        generation = hashlib.sha256(semantic).hexdigest()
        sample = hashlib.sha256(semantic + f"|{counter}".encode()).hexdigest()
        return GameSessionObservation(state, generation, sample, identity)
