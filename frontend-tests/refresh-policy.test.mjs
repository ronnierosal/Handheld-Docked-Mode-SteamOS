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
  gpus = [],
  egpuStatus = "absent",
  displays = [],
  scanComplete = true,
  linkApplicable = false,
  linkState = "unknown",
  mode = "portable",
  blockers = [],
  gameState = "idle",
  gamescopeRunning = true,
  gamescopeConfidence = "verified",
} = {}) {
  return {
    snapshot: {
      support_tier: support,
      game_state: gameState,
      gpus,
      displays,
      gamescope: { running: gamescopeRunning, confidence: gamescopeConfidence },
      disconnect_readiness: { scan_complete: scanComplete },
      sleep_guard: { required, active, confidence },
      egpu_link: { applicable: linkApplicable, state: linkState },
      blockers,
    },
    inference: { mode },
    diagnostics: { hardware_profiles: { egpu: { status: egpuStatus } } },
  };
}

test("verified absent eGPU state polls for new hardware once per second", () => {
  const value = payload();
  assert.equal(connectionProgress(value).label, "eGPU not detected");
  assert.equal(refreshDelayForSnapshot(value), DISCOVERY_REFRESH_MS);
});

test("incomplete identity and TV evidence use the settling cadence", () => {
  const incomplete = payload({
    required: true,
    support: "unsupported",
    egpuStatus: "unknown",
    blockers: [{ code: "egpu_identity_unverified", message: "Exact topology incomplete." }],
  });
  assert.equal(connectionProgress(incomplete).label, "eGPU evidence unavailable");
  assert.match(connectionProgress(incomplete).detail, /exact G1/i);
  assert.equal(refreshDelayForSnapshot(incomplete), SETTLING_REFRESH_MS);

  const tv = payload({
    required: true,
    active: true,
    displays: [{ kind: "external", connected: true, active: null, edid_ready: false }],
    egpuStatus: "exact",
    gpus: [{ role: "external", present: true, confidence: "verified" }],
    linkApplicable: true,
    linkState: "up",
  });
  assert.equal(connectionProgress(tv).label, "TV initializing");
  assert.equal(refreshDelayForSnapshot(tv), SETTLING_REFRESH_MS);
});

test("verified eGPU and TV states expose progressive labels", () => {
  const g1Facts = {
    egpuStatus: "exact",
    gpus: [{ role: "external", present: true, confidence: "verified" }],
    linkApplicable: true,
    linkState: "up",
  };
  const g1 = payload({ required: true, active: true, ...g1Facts });
  assert.equal(connectionProgress(g1).label, "eGPU detected");
  assert.equal(refreshDelayForSnapshot(g1), DISCOVERY_REFRESH_MS);

  const display = { kind: "external", connected: true, active: false, edid_ready: true, confidence: "verified" };
  const ready = payload({ required: true, active: true, displays: [display], ...g1Facts });
  assert.equal(connectionProgress(ready).label, "Ready to dock");
  assert.equal(refreshDelayForSnapshot(ready), DISCOVERY_REFRESH_MS);

  const docked = payload({
    required: true,
    active: true,
    displays: [{ ...display, active: true }],
    mode: "tv_docked",
    ...g1Facts,
  });
  assert.equal(connectionProgress(docked).label, "TV Docked");
  assert.equal(refreshDelayForSnapshot(docked), STABLE_REFRESH_MS);

  const inconsistent = payload({
    required: true,
    active: true,
    displays: [{ ...display, active: true }],
    blockers: [{ code: "render_gpu_unknown", message: "Render GPU is not verified." }],
    ...g1Facts,
  });
  assert.equal(connectionProgress(inconsistent).label, "Dock verification blocked");
  assert.match(connectionProgress(inconsistent).detail, /render gpu/i);
  assert.equal(refreshDelayForSnapshot(inconsistent), SETTLING_REFRESH_MS);
});

test("unverified display activity or Gamescope state never becomes ready to dock", () => {
  const g1Facts = {
    required: true,
    active: true,
    egpuStatus: "exact",
    gpus: [{ role: "external", present: true, confidence: "verified" }],
    linkApplicable: true,
    linkState: "up",
  };
  const observedDisplay = { kind: "external", connected: true, active: false, edid_ready: true, confidence: "observed" };
  assert.equal(connectionProgress(payload({ ...g1Facts, displays: [observedDisplay] })).label, "TV initializing");

  const verifiedDisplay = { ...observedDisplay, confidence: "verified" };
  assert.equal(connectionProgress(payload({
    ...g1Facts,
    displays: [verifiedDisplay],
    gamescopeConfidence: "unknown",
  })).label, "Dock verification blocked");
});

test("a stale display or sleep guard never substitutes for exact current G1 evidence", () => {
  const display = { kind: "external", connected: true, active: false, edid_ready: true, confidence: "verified" };
  const stale = payload({
    required: true,
    active: true,
    displays: [display],
    egpuStatus: "absent",
  });
  assert.equal(connectionProgress(stale).label, "eGPU not detected");

  const unknown = payload({
    required: true,
    active: true,
    displays: [display],
    egpuStatus: "unknown",
  });
  assert.equal(connectionProgress(unknown).label, "eGPU evidence unavailable");
  assert.notEqual(connectionProgress(unknown).label, "Ready to dock");
});

test("link Down or Unknown cannot present a docked connection as ready", () => {
  const display = { kind: "external", connected: true, active: true, edid_ready: true, confidence: "verified" };
  const down = payload({
    required: true,
    active: true,
    displays: [display],
    mode: "tv_docked",
    linkApplicable: true,
    linkState: "down",
    egpuStatus: "exact",
    gpus: [{ role: "external", present: true, confidence: "verified" }],
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
    egpuStatus: "exact",
    gpus: [{ role: "external", present: true, confidence: "verified" }],
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
