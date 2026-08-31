import { callable } from "@decky/api";

export interface BlockerPayload {
  code: string;
  message: string;
}

export interface GpuPayload {
  stable_id: string;
  role: "internal" | "external" | "unknown";
  vendor_device: string;
  present: boolean;
  selected_for_render: boolean | null;
  confidence: "unknown" | "observed" | "verified";
}

export interface DisplayPayload {
  stable_id: string;
  kind: "internal" | "external" | "unknown";
  connector: string;
  connected: boolean | null;
  active: boolean | null;
  edid_ready: boolean | null;
  confidence: "unknown" | "observed" | "verified";
}

export interface SnapshotPayload {
  snapshot: {
    schema_version: number;
    observed_at: string;
    host_profile: string;
    support_tier: string;
    game_state: string;
    gpus: GpuPayload[];
    displays: DisplayPayload[];
    gamescope: {
      running: boolean | null;
      pid: number | null;
      output_order: string[];
      render_gpu_stable_id: string;
      render_vendor_device: string;
      confidence: string;
    };
    blockers: BlockerPayload[];
  };
  inference: {
    mode: string;
    reasons: string[];
  };
}

export const getSnapshot = callable<[], SnapshotPayload>("get_snapshot");
