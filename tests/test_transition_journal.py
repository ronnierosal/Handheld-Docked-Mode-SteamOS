from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from hdm.domain.control_plane import PlacementState, WorkflowState  # noqa: E402
from hdm.domain.transition_journal import (  # noqa: E402
    MAX_JOURNAL_ENTRIES,
    JournalEntry,
    JournalEventKind,
    TransitionJournal,
    append_journal_entry,
    journal_from_dict,
    journal_to_dict,
)


def append(
    journal: TransitionJournal,
    kind: JournalEventKind,
    code: str,
    workflow: WorkflowState = WorkflowState.CONNECTING,
) -> TransitionJournal:
    return append_journal_entry(
        journal,
        kind=kind,
        occurred_at="2026-08-31T12:00:00Z",
        workflow_state=workflow,
        placement=PlacementState.PORTABLE,
        code=code,
    )


class TransitionJournalTests(unittest.TestCase):
    def test_happy_path_round_trips_strict_schema(self):
        journal = TransitionJournal("operation-1", "request-1")
        journal = append(journal, JournalEventKind.REQUESTED, "request.accepted")
        journal = append(journal, JournalEventKind.OBSERVED, "snapshot.observed")
        journal = append(journal, JournalEventKind.VALIDATED, "plan.validated")
        journal = append(journal, JournalEventKind.PLANNED, "plan.ready")
        journal = append(journal, JournalEventKind.STEP_STARTED, "step.started")
        journal = append(journal, JournalEventKind.STEP_VERIFIED, "step.verified")
        journal = append(
            journal,
            JournalEventKind.COMMITTED,
            "transition.committed",
            WorkflowState.IDLE,
        )
        self.assertTrue(journal.terminal)
        self.assertEqual(journal_from_dict(journal_to_dict(journal)), journal)

    def test_out_of_order_and_post_terminal_events_are_rejected(self):
        journal = TransitionJournal("operation-1", "request-1")
        with self.assertRaisesRegex(ValueError, "event order"):
            append(journal, JournalEventKind.PLANNED, "plan.ready")
        journal = append(journal, JournalEventKind.REQUESTED, "request.accepted")
        journal = append(
            journal,
            JournalEventKind.BLOCKED,
            "request.blocked",
            WorkflowState.ACTION_REQUIRED,
        )
        with self.assertRaisesRegex(ValueError, "terminal"):
            append(journal, JournalEventKind.OBSERVED, "snapshot.observed")

    def test_private_or_unbounded_details_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "allowlisted"):
            JournalEntry(
                sequence=1,
                kind=JournalEventKind.REQUESTED,
                occurred_at="2026-08-31T12:00:00Z",
                workflow_state=WorkflowState.IDLE,
                placement=PlacementState.PORTABLE,
                code="request.accepted",
                details=(("command_line", "/home/deck/private"),),
            )
        with self.assertRaisesRegex(ValueError, "categorical"):
            JournalEntry(
                sequence=1,
                kind=JournalEventKind.REQUESTED,
                occurred_at="2026-08-31T12:00:00Z",
                workflow_state=WorkflowState.IDLE,
                placement=PlacementState.PORTABLE,
                code="request.accepted",
                details=(("reason_code", "/home/deck/private"),),
            )

    def test_bound_is_fail_closed_and_never_discards_prior_entries(self):
        entries = [
            JournalEntry(
                sequence=1,
                kind=JournalEventKind.REQUESTED,
                occurred_at="2026-08-31T12:00:00Z",
                workflow_state=WorkflowState.CONNECTING,
                placement=PlacementState.PORTABLE,
                code="request.accepted",
            ),
            JournalEntry(
                sequence=2,
                kind=JournalEventKind.OBSERVED,
                occurred_at="2026-08-31T12:00:00Z",
                workflow_state=WorkflowState.CONNECTING,
                placement=PlacementState.PORTABLE,
                code="snapshot.observed",
            ),
            JournalEntry(
                sequence=3,
                kind=JournalEventKind.VALIDATED,
                occurred_at="2026-08-31T12:00:00Z",
                workflow_state=WorkflowState.CONNECTING,
                placement=PlacementState.PORTABLE,
                code="plan.validated",
            ),
            JournalEntry(
                sequence=4,
                kind=JournalEventKind.PLANNED,
                occurred_at="2026-08-31T12:00:00Z",
                workflow_state=WorkflowState.CONNECTING,
                placement=PlacementState.PORTABLE,
                code="plan.ready",
            ),
        ]
        for sequence in range(5, MAX_JOURNAL_ENTRIES + 1):
            kind = (
                JournalEventKind.STEP_STARTED
                if sequence % 2
                else JournalEventKind.STEP_VERIFIED
            )
            entries.append(
                JournalEntry(
                    sequence=sequence,
                    kind=kind,
                    occurred_at="2026-08-31T12:00:00Z",
                    workflow_state=WorkflowState.CONNECTING,
                    placement=PlacementState.PORTABLE,
                    code="step.event",
                )
            )
        journal = TransitionJournal("operation-1", "request-1", tuple(entries))
        with self.assertRaisesRegex(ValueError, "full"):
            append(journal, JournalEventKind.COMMITTED, "transition.committed")
        self.assertEqual(len(journal.entries), MAX_JOURNAL_ENTRIES)

    def test_parser_rejects_unknown_fields(self):
        value = journal_to_dict(TransitionJournal("operation-1", "request-1"))
        value["private_path"] = "/home/deck"
        with self.assertRaisesRegex(ValueError, "unknown or missing"):
            journal_from_dict(value)


if __name__ == "__main__":
    unittest.main()
