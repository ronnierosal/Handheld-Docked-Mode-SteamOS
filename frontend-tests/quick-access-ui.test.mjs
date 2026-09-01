import assert from "node:assert/strict";
import test from "node:test";

import {
  atAGlanceRows,
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

test("returning to status focuses an in-panel native control, never QAM Back", () => {
  const calls = [];
  const control = { focus: (options) => calls.push(options) };
  assert.equal(restoreQuickAccessFocus(() => control), true);
  assert.deepEqual(calls, [{ preventScroll: true }]);
  assert.equal(restoreQuickAccessFocus(() => null), false);
});
