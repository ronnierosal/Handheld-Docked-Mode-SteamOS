from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from hdm.delivery.transition_journal_store import (  # noqa: E402
    JOURNAL_FILENAME,
    FileTransitionJournalStore,
)
from hdm.domain.control_plane import PlacementState, WorkflowState  # noqa: E402
from hdm.domain.transition_journal import (  # noqa: E402
    JournalEventKind,
    TransitionJournal,
    append_journal_entry,
)


def append(journal, kind, code):
    return append_journal_entry(
        journal,
        kind=kind,
        occurred_at="2026-08-31T12:00:00Z",
        workflow_state=(
            WorkflowState.IDLE
            if kind is JournalEventKind.COMMITTED
            else WorkflowState.CONNECTING
        ),
        placement=PlacementState.PORTABLE,
        code=code,
    )


def requested(operation="operation-1"):
    return append(
        TransitionJournal(operation, "request-1"),
        JournalEventKind.REQUESTED,
        "request.accepted",
    )


def committed(operation="operation-1"):
    journal = requested(operation)
    journal = append(journal, JournalEventKind.OBSERVED, "snapshot.observed")
    journal = append(journal, JournalEventKind.VALIDATED, "plan.validated")
    journal = append(journal, JournalEventKind.PLANNED, "plan.ready")
    return append(journal, JournalEventKind.COMMITTED, "transition.committed")


class TransitionJournalStoreTests(unittest.TestCase):
    def store(self, root, replace=None, tokens=None):
        kwargs = {
            "token_factory": lambda: next(iter(tokens or ["temporary1"])),
        }
        if replace is not None:
            kwargs["replace"] = replace
        return FileTransitionJournalStore(Path(root).resolve(), **kwargs)

    def test_save_load_append_and_idempotent_save(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self.store(directory, tokens=["temporary1"])
            first = requested()
            store.save(first)
            self.assertEqual(store.load_current(), first)
            second = append(first, JournalEventKind.OBSERVED, "snapshot.observed")
            store = self.store(directory, tokens=["temporary2"])
            store.save(second)
            store.save(second)
            self.assertEqual(store.load_current(), second)

    def test_different_regressed_or_divergent_history_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self.store(directory)
            first = requested()
            observed = append(first, JournalEventKind.OBSERVED, "snapshot.observed")
            store.save(observed)
            cases = (
                requested("operation-2"),
                first,
                append(first, JournalEventKind.BLOCKED, "transition.blocked"),
            )
            for replacement in cases:
                with self.subTest(replacement=replacement), self.assertRaises(ValueError):
                    store.save(replacement)
            self.assertEqual(store.load_current(), observed)

    def test_replace_failure_preserves_prior_journal_and_cleans_temp(self):
        with tempfile.TemporaryDirectory() as directory:
            initial_store = self.store(directory, tokens=["temporary1"])
            first = requested()
            initial_store.save(first)

            def fail_replace(_source, _target):
                raise OSError("injected replace failure")

            store = self.store(
                directory, replace=fail_replace, tokens=["temporary2"]
            )
            second = append(first, JournalEventKind.OBSERVED, "snapshot.observed")
            with self.assertRaisesRegex(OSError, "injected"):
                store.save(second)
            self.assertEqual(initial_store.load_current(), first)
            self.assertEqual(
                [path.name for path in Path(directory).iterdir()], [JOURNAL_FILENAME]
            )

    def test_only_matching_terminal_operation_can_be_cleared(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self.store(directory)
            store.save(committed())
            with self.assertRaisesRegex(ValueError, "does not match"):
                store.clear_terminal("different-operation")
            store.clear_terminal("operation-1")
            self.assertIsNone(store.load_current())

            store = self.store(directory, tokens=["temporary2"])
            store.save(requested())
            with self.assertRaisesRegex(ValueError, "incomplete"):
                store.clear_terminal("operation-1")

    def test_corrupt_or_unknown_schema_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / JOURNAL_FILENAME
            for value in (b"not-json", json.dumps({"schema_version": 99}).encode()):
                path.write_bytes(value)
                with self.subTest(value=value), self.assertRaises(ValueError):
                    self.store(directory).load_current()

    def test_relative_or_symlink_root_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "absolute"):
            FileTransitionJournalStore(Path("relative"))
        with tempfile.TemporaryDirectory() as directory:
            real = Path(directory) / "real"
            link = Path(directory) / "link"
            real.mkdir()
            try:
                link.symlink_to(real, target_is_directory=True)
            except OSError:
                self.skipTest("directory symlinks are unavailable on this host")
            with self.assertRaisesRegex(ValueError, "real directory"):
                FileTransitionJournalStore(link.absolute()).load_current()


if __name__ == "__main__":
    unittest.main()
