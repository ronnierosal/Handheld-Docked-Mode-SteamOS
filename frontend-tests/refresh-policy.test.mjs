import assert from "node:assert/strict";
import test from "node:test";

import {
  connectionProgress,
  ACTIVE_GAME_REFRESH_MS,
  BACKGROUND_REFRESH_MS,
  DISCOVERY_REFRESH_MS,
  refreshDelayForVisibility,
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
  linkApplicable = false,
  linkState = "unknown",
  mode = "portable",
  blockers = [],
  gameState = "idle",
} = {}) {
  return {
    snapshot: {
      support_tier: support,
      game_state: gameState,
      displays,
      disconnect_readiness: { scan_complete: scanComplete },
      sleep_guard: { required, active, confidence },
      egpu_link: { applicable: linkApplicable, state: linkState },
      blockers,
    },
    inference: { mode },
  };
}

test("detached state polls for new hardware once per second", () => {
  const value = payload();
  assert.equal(connectionProgress(value).label, "Waiting for eGPU");
  assert.equal(refreshDelayForSnapshot(value), DISCOVERY_REFRESH_MS);
});

test("incomplete identity and TV evidence use the settling cadence", () => {
  const incomplete = payload({
    required: true,
    support: "unsupported",
    blockers: [{ code: "egpu_identity_unverified", message: "Exact topology incomplete." }],
  });
  assert.equal(connectionProgress(incomplete).label, "eGPU verification blocked");
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

test("verified eGPU and TV states expose progressive labels", () => {
  const g1 = payload({ required: true, active: true });
  assert.equal(connectionProgress(g1).label, "eGPU detected");
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

test("link Down or Unknown cannot present a docked connection as ready", () => {
  const display = { kind: "external", connected: true, active: true, edid_ready: true };
  const down = payload({
    required: true,
    active: true,
    displays: [display],
    mode: "tv_docked",
    linkApplicable: true,
    linkState: "down",
  });
  assert.equal(connectionProgress(down).label, "eGPU link needs attention");
  assert.equal(refreshDelayForSnapshot(down), SETTLING_REFRESH_MS);

  const unknown = payload({
    required: true,
    active: true,
    displays: [display],
    mode: "tv_docked",
    linkApplicable: true,
    linkState: "unknown",
  });
  assert.equal(connectionProgress(unknown).label, "eGPU link needs verification");
  assert.doesNotMatch(connectionProgress(unknown).detail.toLowerCase(), /safe|fault|cable/);
});

test("unknown guard and incomplete client scans stay fast and fail closed while idle", () => {
  assert.equal(refreshDelayForSnapshot(payload({ confidence: "unknown" })), SETTLING_REFRESH_MS);
  assert.equal(refreshDelayForSnapshot(payload({ scanComplete: false })), SETTLING_REFRESH_MS);
});

test("running or unknown game evidence never turns deferred diagnostics into rapid polling", () => {
  assert.equal(
    refreshDelayForSnapshot(payload({
      required: true,
      scanComplete: false,
      gameState: "running",
    })),
    ACTIVE_GAME_REFRESH_MS,
  );
  assert.equal(
    refreshDelayForSnapshot(payload({
      required: true,
      scanComplete: false,
      gameState: "unknown",
    })),
    STABLE_REFRESH_MS,
  );
});

test("closed Quick Access uses one low-frequency UI cadence without changing backend safety", () => {
  const running = payload({ gameState: "running" });
  assert.equal(
    refreshDelayForVisibility(running, false),
    BACKGROUND_REFRESH_MS,
  );
  assert.equal(
    refreshDelayForVisibility(running, true),
    ACTIVE_GAME_REFRESH_MS,
  );
  assert.equal(
    refreshDelayForVisibility(payload(), true),
    DISCOVERY_REFRESH_MS,
  );
});
