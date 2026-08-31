from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from hdm.domain.control_plane import PlacementState, WorkflowState  # noqa: E402
from hdm.domain.event_policy import (  # noqa: E402
    RecoveryDirective,
    TopologyEvent,
    decide_topology_event,
)


class EventPolicyTests(unittest.TestCase):
    def test_unexpected_unplug_recovers_portable_and_never_sleeps(self):
        decision = decide_topology_event(
            event=TopologyEvent.EGPU_REMOVED,
            placement=PlacementState.DOCKED_EGPU,
            workflow=WorkflowState.IDLE,
        )
        self.assertEqual(
            decision.directives, (RecoveryDirective.RECOVER_PORTABLE,)
        )
        self.assertNotIn(
            RecoveryDirective.CONTINUE_PENDING_SLEEP_AFTER_RECOVERY,
            decision.directives,
        )

    def test_expected_sleep_disconnect_continues_only_after_portable_recovery(self):
        decision = decide_topology_event(
            event=TopologyEvent.EGPU_REMOVED,
            placement=PlacementState.DOCKED_EGPU,
            workflow=WorkflowState.SLEEP_PENDING_DISCONNECT,
        )
        self.assertEqual(
            decision.directives,
            (
                RecoveryDirective.RECOVER_PORTABLE,
                RecoveryDirective.CONTINUE_PENDING_SLEEP_AFTER_RECOVERY,
            ),
        )
        self.assertEqual(decision.next_workflow, WorkflowState.RETURNING_TO_PORTABLE)

    def test_controller_loss_restores_builtin_only_when_verified_available(self):
        restored = decide_topology_event(
            event=TopologyEvent.EXTERNAL_CONTROLLER_LOST,
            placement=PlacementState.DOCKED_EGPU,
            workflow=WorkflowState.IDLE,
            builtin_controller_available=True,
        )
        self.assertEqual(
            restored.directives, (RecoveryDirective.RESTORE_BUILTIN_CONTROLLER,)
        )
        unknown = decide_topology_event(
            event=TopologyEvent.EXTERNAL_CONTROLLER_LOST,
            placement=PlacementState.DOCKED_EGPU,
            workflow=WorkflowState.IDLE,
            builtin_controller_available=None,
        )
        self.assertEqual(unknown.next_workflow, WorkflowState.ACTION_REQUIRED)

    def test_external_display_loss_recovers_from_both_docked_placements(self):
        for placement in (PlacementState.DOCKED_IGPU, PlacementState.DOCKED_EGPU):
            with self.subTest(placement=placement):
                decision = decide_topology_event(
                    event=TopologyEvent.EXTERNAL_DISPLAY_LOST,
                    placement=placement,
                    workflow=WorkflowState.IDLE,
                )
                self.assertEqual(
                    decision.directives, (RecoveryDirective.RECOVER_PORTABLE,)
                )


if __name__ == "__main__":
    unittest.main()
