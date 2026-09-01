import assert from "node:assert/strict";
import test from "node:test";

import { healthStatusLabel } from "../src/health-ui.ts";


test("primary health label remains categorical and controller-friendly", () => {
  for (const [state, expected] of [
    ["ready", "Ready"],
    ["recovering", "Recovering"],
    ["degraded", "Degraded"],
    ["attention_required", "Needs attention"],
  ]) {
    assert.equal(healthStatusLabel({ state }), expected);
  }
});

test("missing health never resembles a healthy system", () => {
  assert.equal(healthStatusLabel(undefined), "Unavailable");
  assert.equal(healthStatusLabel(undefined, true), "Checking…");
});
