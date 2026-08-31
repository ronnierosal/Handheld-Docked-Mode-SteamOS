export const DISCOVERY_REFRESH_MS = 1_000;
export const SETTLING_REFRESH_MS = 750;
export const STABLE_REFRESH_MS = 3_000;

export interface RefreshPolicyPayload {
  snapshot: {
    support_tier: string;
    game_state: string;
    displays: Array<{
      kind: string;
      connected: boolean | null;
      active: boolean | null;
      edid_ready: boolean | null;
    }>;
    disconnect_readiness: {
      scan_complete: boolean;
    };
    sleep_guard: {
      required: boolean;
      active: boolean;
      confidence: string;
    };
    blockers: Array<{ code: string; message: string }>;
  };
  inference: {
    mode: string;
  };
}

export interface ConnectionProgress {
  label: string;
  detail: string;
  settling: boolean;
}

function firstHardwareBlocker(payload: RefreshPolicyPayload): string {
  const blocker = payload.snapshot.blockers.find((item) => (
    item.code === "egpu_identity_unverified"
    || item.code === "drm_inventory_unavailable"
    || item.code === "active_display_unknown"
    || item.code === "render_gpu_unknown"
    || item.code === "gamescope_unverified"
    || item.code === "render_selector_conflict"
    || item.code === "game_state_unknown"
  ));
  return blocker?.message ?? "Waiting for complete hardware evidence.";
}

export function connectionProgress(
  payload: RefreshPolicyPayload | null,
): ConnectionProgress {
  if (!payload) {
    return { label: "Checking hardware", detail: "Reading current state.", settling: true };
  }

  const { snapshot, inference } = payload;
  if (!snapshot.sleep_guard.required) {
    return {
      label: "Waiting for G1",
      detail: "No GPD G1 candidate is attached.",
      settling: false,
    };
  }
  if (snapshot.support_tier !== "certified") {
    return {
      label: "G1 verification blocked",
      detail: firstHardwareBlocker(payload),
      settling: true,
    };
  }

  const external = snapshot.displays.filter(
    (display) => display.kind === "external" && display.connected === true,
  );
  if (external.length === 0) {
    return {
      label: "G1 detected",
      detail: "Waiting for a connected TV output.",
      settling: false,
    };
  }
  if (
    external.length !== 1
    || external[0].edid_ready !== true
    || external[0].active === null
  ) {
    return {
      label: "TV initializing",
      detail: "Waiting for one verified connector, EDID, and active-output result.",
      settling: true,
    };
  }
  if (inference.mode === "tv_docked") {
    return {
      label: "TV Docked",
      detail: "The live render GPU and TV output are verified.",
      settling: false,
    };
  }
  if (external[0].active === true) {
    return {
      label: "Dock verification blocked",
      detail: firstHardwareBlocker(payload),
      settling: true,
    };
  }
  return {
    label: "Ready to dock",
    detail: "TV evidence is ready. Display transitions remain disabled in this build.",
    settling: false,
  };
}

export function refreshDelayForSnapshot(
  payload: RefreshPolicyPayload | null,
): number {
  if (!payload) {
    return SETTLING_REFRESH_MS;
  }
  const { snapshot } = payload;
  const progress = connectionProgress(payload);
  if (
    progress.settling
    || !snapshot.disconnect_readiness.scan_complete
    || snapshot.sleep_guard.confidence === "unknown"
    || (snapshot.sleep_guard.required && !snapshot.sleep_guard.active)
  ) {
    return SETTLING_REFRESH_MS;
  }
  return progress.label === "TV Docked" ? STABLE_REFRESH_MS : DISCOVERY_REFRESH_MS;
}
