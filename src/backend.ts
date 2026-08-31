import { callable } from "@decky/api";

export interface BlockerPayload {
  code: string;
  message: string;
}

export interface GpuPayload {
  role: "internal" | "external" | "unknown";
  present: boolean;
  selected_for_render: boolean | null;
  confidence: "unknown" | "observed" | "verified";
}

export interface DisplayPayload {
  kind: "internal" | "external" | "unknown";
  connected: boolean | null;
  active: boolean | null;
  edid_ready: boolean | null;
  confidence: "unknown" | "observed" | "verified";
}

export interface EgpuClientPayload {
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
  delivery_schema_version: number;
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
  diagnostics: {
    schema_version: number;
    timings_ms: Array<{
      stage: string;
      duration_ms: number;
    }>;
  };
}

export const getSnapshot = callable<[], SnapshotPayload>("get_snapshot");

export interface SupportBundlePreviewPayload {
  schema_version: number;
  preview_token: string;
  preview_json: string;
  size_bytes: number;
  event_count: number;
  manifest: {
    redacted: boolean;
    bounded: boolean;
    contents: string[];
  };
}

export interface SupportBundleSavePayload {
  ok: boolean;
  relative_path: string;
  size_bytes: number;
}

export const previewSupportBundle = callable<[], SupportBundlePreviewPayload>(
  "preview_support_bundle",
);
export const saveSupportBundle = callable<[string], SupportBundleSavePayload>(
  "save_support_bundle",
);

export interface PresentationPreparationPreviewPayload {
  schema_version: number;
  ready: boolean;
  blockers: string[];
  confirmation_required: boolean;
}

export interface PresentationPreparationApprovalPayload {
  schema_version: number;
  approval_token: string;
  ready: boolean;
  blockers: string[];
}

export interface PresentationPreparationOutcomePayload {
  schema_version: number;
  prepared: boolean;
  changed: boolean;
  code: string;
  rollback_attempted: boolean;
  rollback_succeeded: boolean;
}

export const previewPresentationPreparation = callable<
  [],
  PresentationPreparationPreviewPayload
>("preview_presentation_preparation");
export const approvePresentationPreparation = callable<
  [],
  PresentationPreparationApprovalPayload
>("approve_presentation_preparation");
export const preparePresentationIntegration = callable<
  [string],
  PresentationPreparationOutcomePayload
>("prepare_presentation_integration");
