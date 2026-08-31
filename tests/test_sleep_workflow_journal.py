from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from hdm.application.sleep_workflow_journal import (  # noqa: E402
    advance_sleep_journal,
    recover_interrupted_sleep_journal,
    start_sleep_journal,
)
from hdm.delivery.transition_journal_store import (  # noqa: E402
    FileTransitionJournalStore,
)
from hdm.domain.control_plane import PlacementState  # noqa: E402
from hdm.domain.game_compatibility import GameSaveCapability  # noqa: E402
from hdm.domain.sleep_workflow import SleepFlow, SleepFlowStage  # noqa: E402
from hdm.domain.transition_journal import JournalEventKind  # noqa: E402


def flow(
    stage: SleepFlowStage,
    *,
    reason: str = "sleep.test",
    pending: bool = True,
    history: tuple[SleepFlowStage, ...] = (),
) -> SleepFlow:
    return SleepFlow(
        request_id="sleep-request-1",
        stage=stage,
        directives=(),
        original_request_pending=pending,
        reason_code=reason,
        requested_at_ms=0,
        expires_at_ms=900_000,
        history=history,
        save_capability=GameSaveCapability.UNTESTED,
    )


class SleepWorkflowJournalTests(unittest.TestCase):
    def test_live_removal_path_persists_exact_append_only_progress(self):
        waiting = flow(SleepFlowStage.AWAITING_DISCONNECT)
        journal = start_sleep_journal(
            "sleep-operation-1",
            waiting,
            PlacementState.DOCKED_EGPU,
            occurred_at="test",
        )
        with tempfile.TemporaryDirectory() as root:
            store = FileTransitionJournalStore(Path(root).resolve())
            store.save(journal)
            restoring = flow(
                SleepFlowStage.RESTORING_PORTABLE,
                history=(SleepFlowStage.AWAITING_DISCONNECT,),
            )
            journal = advance_sleep_journal(
                journal,
                waiting,
                restoring,
                PlacementState.UNKNOWN,
                occurred_at="test",
            )
            store.save(journal)
            ready = flow(
                SleepFlowStage.READY_TO_CONTINUE_SLEEP,
                history=(
                    SleepFlowStage.AWAITING_DISCONNECT,
                    SleepFlowStage.RESTORING_PORTABLE,
                ),
            )
            journal = advance_sleep_journal(
                journal,
                restoring,
                ready,
                PlacementState.PORTABLE,
                occurred_at="test",
            )
            store.save(journal)
            completed = flow(
                SleepFlowStage.COMPLETED,
                pending=False,
                history=(
                    SleepFlowStage.AWAITING_DISCONNECT,
                    SleepFlowStage.RESTORING_PORTABLE,
                    SleepFlowStage.READY_TO_CONTINUE_SLEEP,
                ),
            )
            journal = advance_sleep_journal(
                journal,
                ready,
                completed,
                PlacementState.PORTABLE,
                occurred_at="test",
            )
            store.save(journal)
            self.assertEqual(store.load_current(), journal)
            self.assertEqual(journal.entries[-1].kind, JournalEventKind.COMMITTED)

    def test_g1_shutdown_first_is_terminal_blocked_not_safe(self):
        shutdown = flow(
            SleepFlowStage.SHUTDOWN_REQUIRED,
            reason="disconnect.shutdown_required",
            pending=False,
        )
        journal = start_sleep_journal(
            "sleep-operation-1",
            shutdown,
            PlacementState.DOCKED_EGPU,
            occurred_at="test",
        )
        self.assertEqual(journal.entries[-1].kind, JournalEventKind.BLOCKED)
        self.assertEqual(
            journal.entries[-1].workflow_state.value,
            "sleep_pending_disconnect",
        )
        self.assertNotIn("safe", journal.entries[-1].code)

    def test_cancelled_active_step_cannot_reactivate_request(self):
        waiting = flow(SleepFlowStage.AWAITING_GAME_CONSENT)
        journal = start_sleep_journal(
            "sleep-operation-1",
            waiting,
            PlacementState.DOCKED_EGPU,
            occurred_at="test",
        )
        cancelled = flow(
            SleepFlowStage.CANCELLED,
            reason="game.consent_denied",
            pending=False,
            history=(SleepFlowStage.AWAITING_GAME_CONSENT,),
        )
        journal = advance_sleep_journal(
            journal,
            waiting,
            cancelled,
            PlacementState.DOCKED_EGPU,
            occurred_at="test",
        )
        self.assertEqual(journal.entries[-1].kind, JournalEventKind.BLOCKED)
        with self.assertRaisesRegex(ValueError, "terminal"):
            advance_sleep_journal(
                journal,
                cancelled,
                cancelled,
                PlacementState.DOCKED_EGPU,
                occurred_at="test",
            )

    def test_restart_never_commits_or_continues_original_sleep(self):
        waiting = flow(SleepFlowStage.AWAITING_DISCONNECT)
        journal = start_sleep_journal(
            "sleep-operation-1",
            waiting,
            PlacementState.DOCKED_EGPU,
            occurred_at="test",
        )
        recovered = recover_interrupted_sleep_journal(
            journal,
            PlacementState.PORTABLE,
            exact_egpu_absence_verified=True,
            occurred_at="restart",
        )
        self.assertEqual(
            recovered.entries[-1].kind,
            JournalEventKind.RECOVERY_VERIFIED,
        )
        self.assertNotIn(
            JournalEventKind.COMMITTED,
            tuple(entry.kind for entry in recovered.entries),
        )

    def test_restart_without_verified_portable_state_requires_action(self):
        waiting = flow(SleepFlowStage.AWAITING_DISCONNECT)
        journal = start_sleep_journal(
            "sleep-operation-1",
            waiting,
            PlacementState.DOCKED_EGPU,
            occurred_at="test",
        )
        failed = recover_interrupted_sleep_journal(
            journal,
            PlacementState.UNKNOWN,
            exact_egpu_absence_verified=False,
            occurred_at="restart",
        )
        self.assertEqual(failed.entries[-1].kind, JournalEventKind.FAILED)
        self.assertEqual(
            failed.entries[-1].workflow_state.value,
            "action_required",
        )

    def test_flow_and_active_step_must_match_exactly(self):
        waiting = flow(SleepFlowStage.AWAITING_DISCONNECT)
        journal = start_sleep_journal(
            "sleep-operation-1",
            waiting,
            PlacementState.DOCKED_EGPU,
            occurred_at="test",
        )
        wrong = flow(SleepFlowStage.CLOSING_GAME)
        with self.assertRaisesRegex(ValueError, "active step"):
            advance_sleep_journal(
                journal,
                wrong,
                flow(
                    SleepFlowStage.RELEASING_CLIENTS,
                    history=(SleepFlowStage.CLOSING_GAME,),
                ),
                PlacementState.DOCKED_EGPU,
                occurred_at="test",
            )


if __name__ == "__main__":
    unittest.main()
