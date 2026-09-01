import assert from "node:assert/strict";
import test from "node:test";

import { decideLinkHealthNotification } from "../src/link-health-notification.ts";

function payload({ applicable = true, state = "up", reason = "egpu.link_observed", mode = "tv_docked" } = {}) {
  return {
    snapshot: { egpu_link: { applicable, state, reason, error: "" } },
    inference: { mode },
  };
}

test("first relevant link observation establishes a silent baseline", () => {
  const result = decideLinkHealthNotification(null, payload());
  assert.deepEqual(result.memory, { state: "up", reason: "egpu.link_observed", instabilityNotified: false });
  assert.equal(result.notification, null);
});

test("one instability episode suppresses Down/Unknown flapping until recovery", () => {
  const baseline = decideLinkHealthNotification(null, payload());
  const down = decideLinkHealthNotification(
    baseline.memory,
    payload({ state: "down", reason: "egpu.link_down" }),
  );
  assert.equal(down.notification?.title, "eGPU link is down");
  assert.equal(down.notification?.critical, false);
  assert.equal(
    decideLinkHealthNotification(down.memory, payload({ state: "down", reason: "egpu.link_down" })).notification,
    null,
  );
  assert.equal(
    decideLinkHealthNotification(down.memory, payload({ state: "down", reason: "egpu.link_new_reason" })).notification,
    null,
  );
  const unknown = decideLinkHealthNotification(
    down.memory,
    payload({ state: "unknown", reason: "egpu.link_metrics_unavailable" }),
  );
  assert.equal(unknown.notification, null);
  assert.equal(decideLinkHealthNotification(unknown.memory, payload()).notification?.title, "eGPU link observed again");
});

test("unknown link state is attention-only and recovery is announced once", () => {
  const baseline = decideLinkHealthNotification(null, payload());
  const unknown = decideLinkHealthNotification(
    baseline.memory,
    payload({ state: "unknown", reason: "egpu.link_metrics_unavailable" }),
  );
  assert.equal(unknown.notification?.title, "eGPU link needs verification");
  assert.equal(unknown.notification?.critical, false);
  const recovered = decideLinkHealthNotification(unknown.memory, payload());
  assert.equal(recovered.notification?.title, "eGPU link observed again");
  assert.equal(decideLinkHealthNotification(recovered.memory, payload()).notification, null);
});

test("absent and non-eGPU placements do not alert", () => {
  const previous = { state: "up", reason: "egpu.link_observed" };
  assert.deepEqual(
    decideLinkHealthNotification(previous, payload({ applicable: false })),
    { memory: null, notification: null },
  );
  assert.deepEqual(
    decideLinkHealthNotification(previous, payload({ state: "down", mode: "portable" })),
    { memory: previous, notification: null },
  );
});

test("notification language is non-diagnostic and makes no safety claim", () => {
  const baseline = decideLinkHealthNotification(null, payload());
  const notice = decideLinkHealthNotification(
    baseline.memory,
    payload({ state: "down", reason: "egpu.link_down" }),
  ).notification;
  const text = `${notice?.title} ${notice?.body}`.toLowerCase();
  assert.match(text, /preserving the current setup/);
  assert.match(text, /avoid disconnecting/);
  assert.doesNotMatch(text, /cable|fault|safe|eject|recover/);
});
