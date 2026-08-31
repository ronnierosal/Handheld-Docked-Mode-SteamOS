import assert from "node:assert/strict";
import test from "node:test";

import {
  canOfferForce,
  processReleaseOutcomeMessage,
} from "../src/process-release-ui.ts";


function outcome(overrides = {}) {
  return {
    schema_version: 1,
    accepted: true,
    code: "process_release.completed",
    acknowledgement_id: "operation-public-1",
    status: "completed",
    software_blockers_cleared: false,
    hardware_removal_authorized: false,
    remaining_client_count: 1,
    force_receipt_token: "",
    action_required: false,
    ...overrides,
  };
}

test("cleared software blockers never imply physical removal authority", () => {
  const value = outcome({ software_blockers_cleared: true, remaining_client_count: 0 });
  assert.match(processReleaseOutcomeMessage(value), /still not authorized/i);
  assert.equal(canOfferForce(value), false);
});

test("force is offered only with a receipt and terminal acknowledgement", () => {
  const value = outcome({ force_receipt_token: "force-receipt" });
  assert.equal(canOfferForce(value), true);
  assert.match(processReleaseOutcomeMessage(value), /separate confirmation/i);
  assert.equal(canOfferForce(outcome({ force_receipt_token: "force-receipt", acknowledgement_id: "" })), false);
});

test("action-required outcome keeps disconnect prohibited", () => {
  assert.match(
    processReleaseOutcomeMessage(outcome({ action_required: true })),
    /do not disconnect/i,
  );
});
