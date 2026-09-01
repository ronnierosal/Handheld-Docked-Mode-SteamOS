import assert from "node:assert/strict";
import test from "node:test";

import {
  atAGlanceRows,
  compactStatusPanels,
  journeyStatusRows,
  restoreQuickAccessFocus,
} from "../src/quick-access-ui.ts";

test("at-a-glance UI remains compact and preserves progressive state labels", () => {
  assert.deepEqual(
    atAGlanceRows({
      mode: "Portable",
      health: "Ready",
      connection: "Ready to dock",
      game: "No game running",
    }),
    [
      ["Mode", "Portable"],
      ["Health", "Ready"],
      ["Connection", "Ready to dock"],
      ["Game", "No game running"],
    ],
  );
});

test("journey status is glanceable, fail-closed, and keeps detail on demand", () => {
  const rows = journeyStatusRows({
    deferred_dock: { state: "deferred", code: "private.code" },
    prepared_docked_idle: { state: "prepared", code: "private.code" },
    safe_undock: { state: "ready_for_revalidation", code: "private.code" },
    unexpected_removal_recovery: { state: "recovery_incomplete", code: "private.code" },
  });
  assert.deepEqual(rows.map(({ name, value }) => [name, value]), [
    ["Dock request", "Waiting for game to close"],
    ["Prepared state", "Prepared evidence"],
    ["Safe Undock evidence", "Needs revalidation"],
    ["Recovery", "Recovery incomplete"],
  ]);
  assert.doesNotMatch(JSON.stringify(rows), /private\.code/);
  assert.match(rows[2].detail, /not a physical-unplug approval/i);
});

test("unwired or unknown journey states never resemble a hardware result", () => {
  const rows = journeyStatusRows({ safe_undock: { state: "future_state", code: "x" } });
  assert.equal(rows[0].value, "Not connected");
  assert.equal(rows[2].value, "Not connected");
  assert.match(rows[2].detail, /not yet wired/i);
});

test("returning to status focuses an in-panel native control, never QAM Back", () => {
  assert.deepEqual(compactStatusPanels(), {
    showDiagnostics: false,
    showJourneyDetails: false,
  });
  const calls = [];
  const control = { focus: (options) => calls.push(options) };
  assert.equal(restoreQuickAccessFocus(() => control), true);
  assert.deepEqual(calls, [{ preventScroll: true }]);
  assert.equal(restoreQuickAccessFocus(() => null), false);
});
