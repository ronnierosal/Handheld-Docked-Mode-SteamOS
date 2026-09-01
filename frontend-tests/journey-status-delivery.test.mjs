import assert from "node:assert/strict";
import test from "node:test";

import { sanitizeJourneyStatus } from "../src/journey-status-delivery.ts";
import { journeyStatusRows } from "../src/quick-access-ui.ts";

test("journey delivery keeps only recognized public categorical fields", () => {
  const sanitized = sanitizeJourneyStatus({
    safe_undock: { state: "not_ready", code: "private.client.pid.123" },
    offline_readiness: {
      schema_version: 1,
      status: "ready_to_try_offline",
      reason_codes: ["private-title", "private-path"],
      title: "private title",
    },
    extra: { device: "private-device" },
  });
  assert.deepEqual(sanitized, {
    safe_undock: { state: "not_ready", code: "" },
    offline_readiness: { schema_version: 1, status: "ready_to_try_offline", reason_codes: [] },
  });
  assert.doesNotMatch(JSON.stringify(sanitized), /private/);
});

test("malformed, future, and incomplete optional payloads fail closed", () => {
  assert.equal(sanitizeJourneyStatus(null), undefined);
  assert.equal(sanitizeJourneyStatus({ safe_undock: { state: "future_state", code: "x" } }), undefined);
  assert.equal(sanitizeJourneyStatus({ link_instability: { schema_version: 1, status: "stable_observed", current_state: "unknown" } }), undefined);
  const rows = journeyStatusRows(sanitizeJourneyStatus({ safe_undock: { state: "future_state" } }));
  assert.equal(rows[2].value, "Not connected");
});
