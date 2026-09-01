import assert from "node:assert/strict";
import test from "node:test";

import { decideSleepRecoveryNotification } from "../src/sleep-recovery-notification.ts";

function checkpoint({ kind = "portable_verified", code = "sleep.restart_portable_verified", acknowledgement_required = true } = {}) {
  return { schema_version: 1, kind, code, acknowledgement_required };
}

test("an acknowledged recovery checkpoint notifies once per incident", () => {
  const first = decideSleepRecoveryNotification(null, checkpoint());
  assert.equal(first.notification?.title, "Interrupted sleep request closed");
  assert.equal(decideSleepRecoveryNotification(first.memory, checkpoint()).notification, null);
  assert.equal(
    decideSleepRecoveryNotification(first.memory, checkpoint({ kind: "action_required", code: "sleep.restart_action_required" })).notification?.title,
    "Interrupted sleep request needs attention",
  );
});

test("none clears in-process suppression so a new durable incident can notify", () => {
  const first = decideSleepRecoveryNotification(null, checkpoint());
  const cleared = decideSleepRecoveryNotification(first.memory, checkpoint({ kind: "none", code: "", acknowledgement_required: false }));
  assert.equal(cleared.memory, null);
  assert.equal(decideSleepRecoveryNotification(cleared.memory, checkpoint()).notification?.title, "Interrupted sleep request closed");
});

test("wording is honest about recovery and game outcome", () => {
  const portable = decideSleepRecoveryNotification(null, checkpoint()).notification;
  const attention = decideSleepRecoveryNotification(null, checkpoint({ kind: "action_required", code: "sleep.restart_action_required" })).notification;
  assert.match(`${portable?.title} ${portable?.body}`.toLowerCase(), /game\/session outcome was not verified/);
  assert.match(`${attention?.title} ${attention?.body}`.toLowerCase(), /did not continue sleep or claim handheld recovery/);
  assert.doesNotMatch(`${portable?.title} ${portable?.body}`.toLowerCase(), /crash|g1|safe|eject/);
});
