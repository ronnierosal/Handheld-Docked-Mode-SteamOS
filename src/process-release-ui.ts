import type { ProcessReleaseExecutionPayload } from "./backend";


export function processReleaseOutcomeMessage(
  outcome: ProcessReleaseExecutionPayload,
): string {
  if (!outcome.accepted) {
    return "Process-release approval expired or was rejected. Inspect again.";
  }
  if (outcome.software_blockers_cleared) {
    return "Software blockers cleared. Physical G1 removal is still not authorized; shut down before disconnecting.";
  }
  if (outcome.force_receipt_token) {
    return "A process still holds the G1. Force close requires a separate confirmation and may lose unsaved work.";
  }
  if (outcome.action_required) {
    return "Process release needs attention. Acknowledge the result, inspect again, and do not disconnect the G1.";
  }
  return "Software blockers remain. Acknowledge the result and inspect again; do not disconnect the G1.";
}

export function canOfferForce(outcome: ProcessReleaseExecutionPayload): boolean {
  return Boolean(
    outcome.accepted
    && !outcome.software_blockers_cleared
    && outcome.force_receipt_token
    && outcome.acknowledgement_id
  );
}
