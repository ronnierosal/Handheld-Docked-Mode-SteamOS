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

export interface EgpuClientPayload {
  instance_id: string;
  pid: number;
  name: string;
  kind: "game" | "user" | "protected" | "system" | "unknown";
  resources: Array<
    | "drm_card"
    | "drm_render"
    | "drm_control"
    | "audio_pcm"
    | "audio_control"
    | "audio_hardware"
  >;
  close_eligible: boolean;
  reason: string;
}

export interface DisconnectReadinessPayload {
  applicable: boolean;
  scan_complete: boolean;
  ready: boolean;
  egpu_stable_id: string;
  clients: EgpuClientPayload[];
  storage_devices: number;
  storage_in_use: boolean;
  error: string;
}

export interface SleepGuardPayload {
  required: boolean;
  active: boolean;
  confidence: "unknown" | "observed" | "verified";
  reason: string;
  error: string;
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
    disconnect_readiness: DisconnectReadinessPayload;
    sleep_guard: SleepGuardPayload;
    blockers: BlockerPayload[];
  };
  inference: {
    mode: string;
    reasons: string[];
  };
}

export const getSnapshot = callable<[], SnapshotPayload>("get_snapshot");
