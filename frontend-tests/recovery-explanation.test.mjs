import assert from "node:assert/strict";
import test from "node:test";

import { decideRecoveryExplanation } from "../src/recovery-explanation.ts";

test("link instability explains one public episode and stable evidence clears it", () => {
  const first = decideRecoveryExplanation(null, { kind: "link", state: "instability_observed" });
  assert.equal(first.explanation?.title, "eGPU link changed");
  assert.equal(decideRecoveryExplanation(first.memory, { kind: "link", state: "instability_observed" }).explanation, null);
  assert.deepEqual(
    decideRecoveryExplanation(first.memory, { kind: "link", state: "stable_observed" }),
    { memory: null, explanation: null },
  );
});

test("sleep and portable recovery explanations remain calm and do not claim game or hardware success", () => {
  const sleep = decideRecoveryExplanation(null, { kind: "sleep", state: "portable_verified" });
  const recovery = decideRecoveryExplanation(null, { kind: "portable_recovery", state: "portable_fallback_verified" });
  const text = `${sleep.explanation?.body} ${recovery.explanation?.body}`.toLowerCase();
  assert.match(text, /game\/session outcome remains unknown/);
  assert.match(text, /does not claim hardware recovery or game survival/);
  assert.doesNotMatch(text, /safe to unplug|eject|auto-launch|crash/);
});

test("incomplete, unavailable, and unknown categories are deduplicated without raw code exposure", () => {
  const incomplete = decideRecoveryExplanation(null, { kind: "portable_recovery", state: "recovery_incomplete" });
  assert.equal(incomplete.explanation?.title, "Handheld recovery incomplete");
  const unknown = decideRecoveryExplanation(incomplete.memory, { kind: "portable_recovery", state: "private.failure.code" });
  assert.equal(unknown.explanation?.title, "Recovery evidence needs verification");
  assert.doesNotMatch(JSON.stringify(unknown), /private\.failure\.code/);
  assert.equal(
    decideRecoveryExplanation(unknown.memory, { kind: "portable_recovery", state: "different.private.code" }).explanation,
    null,
  );
});
