import assert from "node:assert/strict";
import test from "node:test";

import { diagnosticOverlayRows } from "../src/diagnostics-overlay.ts";


function payload() {
  return {
    snapshot: {
      schema_version: 3,
      observed_at: "2026-08-31T12:00:00Z",
      host_profile: "asus-rog-ally-x",
      support_tier: "certified",
      game_state: "idle",
      gpus: [
        {
          stable_id: "private-gpu-id",
          role: "external",
          vendor_device: "1002:7480",
          present: true,
          selected_for_render: true,
          confidence: "verified",
        },
      ],
      displays: [
        {
          stable_id: "private-display-id",
          connector: "HDMI-A-9",
          kind: "external",
          connected: true,
          active: true,
          edid_ready: true,
          confidence: "verified",
        },
      ],
      gamescope: {
        running: true,
        pid: 1234,
        output_order: ["HDMI-A-9"],
        render_gpu_stable_id: "private-gpu-id",
        render_vendor_device: "1002:7480",
        confidence: "verified",
      },
      disconnect_readiness: {
        applicable: true,
        scan_complete: true,
        ready: false,
        egpu_stable_id: "private-gpu-id",
        clients: [
          {
            instance_id: "private-instance-id",
            pid: 9876,
            name: "sample-client",
            kind: "user",
            resources: ["drm_render"],
            close_eligible: true,
            reason: "fixture",
          },
        ],
        storage_devices: 0,
        storage_in_use: false,
        error: "",
      },
      sleep_guard: {
        required: true,
        active: true,
        confidence: "verified",
        reason: "fixture",
        error: "",
      },
      blockers: [{ code: "test.blocker", message: "Fixture blocker" }],
    },
    inference: { mode: "tv_docked", reasons: [] },
    diagnostics: {
      schema_version: 1,
      timings_ms: [{ stage: "snapshot_total", duration_ms: 25.4 }],
    },
  };
}

test("overlay is empty until a snapshot exists", () => {
  assert.deepEqual(diagnosticOverlayRows(null), []);
});

test("overlay exposes useful categorical state without raw identities", () => {
  const rows = diagnosticOverlayRows(payload());
  const text = JSON.stringify(rows);
  assert.match(text, /asus-rog-ally-x/);
  assert.match(text, /test\.blocker/);
  assert.match(text, /sample-client/);
  assert.match(text, /drm render/);
  assert.match(text, /snapshot_total 25ms/);
  for (const forbidden of [
    "private-gpu-id",
    "private-display-id",
    "private-instance-id",
    "HDMI-A-9",
    "1002:7480",
    "1234",
    "9876",
  ]) {
    assert.doesNotMatch(text, new RegExp(forbidden.replaceAll(":", "\\:")));
  }
});
