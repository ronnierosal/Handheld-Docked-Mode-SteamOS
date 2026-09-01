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

export interface EgpuLinkPayload {
  applicable: boolean;
  state: "up" | "down" | "unknown";
  confidence: "unknown" | "observed" | "verified";
  reason: string;
  error: string;
}

export type ProfileResolutionStatus = "exact" | "absent" | "unknown";

export type HardwareCapabilityAxis =
  | "egpu_support"
  | "egpu_transport"
  | "external_display_output"
  | "display_handoff"
  | "external_audio_output"
  | "audio_handoff"
  | "internal_controller_suppression"
  | "external_controller_promotion"
  | "external_controller_disconnect"
  | "external_controller_power_off"
  | "power_button_interception"
  | "sleep_behavior"
  | "removal_behavior";

export interface HardwareCapabilityDiagnostic {
  axis: HardwareCapabilityAxis;
  value: string;
  confidence: "unknown" | "observed" | "verified";
  basis:
    | "exact_host_profile"
    | "exact_egpu_profile"
    | "composed_exact_profiles"
    | "incomplete_profile_set";
}

export interface HardwareProfileDiagnostics {
  schema_version: number;
  host: {
    status: ProfileResolutionStatus;
    profile_id: string;
  };
  egpu: {
    status: ProfileResolutionStatus;
    profile_id: string;
  };
  capabilities: HardwareCapabilityDiagnostic[];
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
    egpu_link: EgpuLinkPayload;
    blockers: BlockerPayload[];
  };
  inference: {
    mode: string;
    reasons: string[];
  };
  health?: {
    state: "ready" | "recovering" | "degraded" | "attention_required";
    components: Array<{
      component: string;
      state: "ready" | "recovering" | "degraded" | "unknown";
      reason: string;
    }>;
    blockers: string[];
  };
  attach_readiness?: {
    schema_version: number;
    stage: "idle" | "settling" | "waiting_for_external_display" | "ready_idle" | "game_running" | "action_required";
    code: string;
    poll_after_ms: number;
  };
  diagnostics: {
    schema_version: number;
    timings_ms: Array<{
      stage: string;
      duration_ms: number;
    }>;
    hardware_profiles: HardwareProfileDiagnostics;
    build?: {
      schema_version: number;
      version: string;
      revision: string;
    };
  };
}

export const getSnapshot = callable<[], SnapshotPayload>("get_snapshot");

export interface PeripheralStatusPayload {
  schema_version: number;
  controller: { complete: boolean; exact: boolean; builtin_available: boolean | null; external_connected: boolean | null; code: string };
  audio: { complete: boolean; exact: boolean; external_available: boolean | null; portable_available: boolean | null; code: string };
}

export const getPeripheralStatus = callable<[], PeripheralStatusPayload>("get_peripheral_status");

export interface ActionHistoryEntryPayload {
  occurred_at: string;
  kind: "topology" | "transition" | "recovery" | "sleep" | "process_release" | "peripheral" | "presentation";
  outcome: "started" | "succeeded" | "recovered" | "blocked" | "failed" | "attention_required";
  code: string;
}

export interface ActionHistoryPayload {
  schema_version: number;
  entries: ActionHistoryEntryPayload[];
}

export const getActionHistory = callable<[], ActionHistoryPayload>("get_action_history");

export type DockedIgpuLifecycleStage =
  | "idle"
  | "watching"
  | "promotion_ready"
  | "action_required"
  | "closed";

export interface DockedIgpuStatusPayload {
  schema_version: number;
  stage: DockedIgpuLifecycleStage;
  code: string;
  poll_after_ms: number;
  inspection_available: boolean;
  acknowledgement_required: boolean;
}

export interface DockedIgpuAcknowledgementPayload {
  schema_version: number;
  acknowledged: boolean;
}

export const getDockedIgpuStatus = callable<[], DockedIgpuStatusPayload>(
  "get_docked_igpu_status",
);
export const acknowledgeDockedIgpuStatus = callable<
  [],
  DockedIgpuAcknowledgementPayload
>("acknowledge_docked_igpu_status");

export type DiagnosticLoggingDuration =
  | "30_minutes"
  | "1_hour"
  | "2_hours"
  | "until_reboot";

export interface DiagnosticLoggingStatusPayload {
  schema_version: number;
  enabled: boolean;
  mode: "off" | "ttl" | "until_reboot";
  duration: DiagnosticLoggingDuration | "";
  remaining_seconds: number | null;
  code: string;
}

export const getDiagnosticLoggingStatus = callable<
  [],
  DiagnosticLoggingStatusPayload
>("get_diagnostic_logging_status");
export const enableDiagnosticLogging = callable<
  [DiagnosticLoggingDuration, boolean],
  DiagnosticLoggingStatusPayload
>("enable_diagnostic_logging");
export const disableDiagnosticLogging = callable<
  [],
  DiagnosticLoggingStatusPayload
>("disable_diagnostic_logging");

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

export type ProcessReleasePhase = "graceful" | "force";

export interface ProcessReleaseTargetPayload {
  name: string;
  resources: string[];
}

export interface ProcessReleasePreviewPayload {
  schema_version: number;
  phase: ProcessReleasePhase | "";
  ready: boolean;
  approval_token: string;
  expires_in_seconds: number;
  targets: ProcessReleaseTargetPayload[];
  protected_client_count: number;
  blockers: string[];
  confirmation_required: boolean;
}

export interface ProcessReleaseExecutionPayload {
  schema_version: number;
  accepted: boolean;
  code: string;
  acknowledgement_id: string;
  status: string;
  software_blockers_cleared: boolean;
  hardware_removal_authorized: false;
  remaining_client_count: number | null;
  force_receipt_token: string;
  action_required: boolean;
}

export interface ProcessReleaseStatusPayload {
  schema_version: number;
  code: string;
  acknowledgement_required: boolean;
  action_required: boolean;
  acknowledgement_id: string;
  durable: boolean;
}

export interface ProcessReleaseAcknowledgementPayload {
  schema_version: number;
  acknowledged: boolean;
}

export const getProcessReleaseStatus = callable<[], ProcessReleaseStatusPayload>(
  "get_process_release_status",
);
export const previewProcessRelease = callable<
  [ProcessReleasePhase, string],
  ProcessReleasePreviewPayload
>("preview_process_release");
export const approveProcessRelease = callable<
  [ProcessReleasePhase, string],
  ProcessReleasePreviewPayload
>("approve_process_release");
export const executeProcessRelease = callable<
  [string],
  ProcessReleaseExecutionPayload
>("execute_process_release");
export const acknowledgeProcessRelease = callable<
  [string],
  ProcessReleaseAcknowledgementPayload
>("acknowledge_process_release");
