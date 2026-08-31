import assert from "node:assert/strict";
import test from "node:test";

import {
  connectionProgress,
  DISCOVERY_REFRESH_MS,
  refreshDelayForSnapshot,
  SETTLING_REFRESH_MS,
  STABLE_REFRESH_MS,
} from "../src/refresh-policy.ts";


function payload({
  required = false,
  active = false,
  confidence = "verified",
  support = "certified",
  displays = [],
  scanComplete = true,
  mode = "portable",
  blockers = [],
} = {}) {
  return {
    snapshot: {
      support_tier: support,
      game_state: "idle",
      displays,
      disconnect_readiness: { scan_complete: scanComplete },
      sleep_guard: { required, active, confidence },
      blockers,
    },
    inference: { mode },
  };
}

test("detached state polls for new hardware once per second", () => {
  const value = payload();
  assert.equal(connectionProgress(value).label, "Waiting for G1");
  assert.equal(refreshDelayForSnapshot(value), DISCOVERY_REFRESH_MS);
});

test("incomplete identity and TV evidence use the settling cadence", () => {
  const incomplete = payload({
    required: true,
    support: "unsupported",
    blockers: [{ code: "egpu_identity_unverified", message: "Exact topology incomplete." }],
  });
  assert.equal(connectionProgress(incomplete).label, "G1 verification blocked");
  assert.match(connectionProgress(incomplete).detail, /topology incomplete/i);
  assert.equal(refreshDelayForSnapshot(incomplete), SETTLING_REFRESH_MS);

  const tv = payload({
    required: true,
    active: true,
    displays: [{ kind: "external", connected: true, active: null, edid_ready: false }],
  });
  assert.equal(connectionProgress(tv).label, "TV initializing");
  assert.equal(refreshDelayForSnapshot(tv), SETTLING_REFRESH_MS);
});

test("verified G1 and TV states expose progressive labels", () => {
  const g1 = payload({ required: true, active: true });
  assert.equal(connectionProgress(g1).label, "G1 detected");
  assert.equal(refreshDelayForSnapshot(g1), DISCOVERY_REFRESH_MS);

  const display = { kind: "external", connected: true, active: false, edid_ready: true };
  const ready = payload({ required: true, active: true, displays: [display] });
  assert.equal(connectionProgress(ready).label, "Ready to dock");
  assert.equal(refreshDelayForSnapshot(ready), DISCOVERY_REFRESH_MS);

  const docked = payload({
    required: true,
    active: true,
    displays: [{ ...display, active: true }],
    mode: "tv_docked",
  });
  assert.equal(connectionProgress(docked).label, "TV Docked");
  assert.equal(refreshDelayForSnapshot(docked), STABLE_REFRESH_MS);

  const inconsistent = payload({
    required: true,
    active: true,
    displays: [{ ...display, active: true }],
    blockers: [{ code: "render_gpu_unknown", message: "Render GPU is not verified." }],
  });
  assert.equal(connectionProgress(inconsistent).label, "Dock verification blocked");
  assert.match(connectionProgress(inconsistent).detail, /render gpu/i);
  assert.equal(refreshDelayForSnapshot(inconsistent), SETTLING_REFRESH_MS);
});

test("unknown guard and incomplete client scans stay fast and fail closed", () => {
  assert.equal(refreshDelayForSnapshot(payload({ confidence: "unknown" })), SETTLING_REFRESH_MS);
  assert.equal(refreshDelayForSnapshot(payload({ scanComplete: false })), SETTLING_REFRESH_MS);
});
