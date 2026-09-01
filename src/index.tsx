import { definePlugin, toaster } from "@decky/api";
import {
  ButtonItem,
  ConfirmModal,
  DropdownItem,
  PanelSection,
  PanelSectionRow,
  ScrollPanel,
  showModal,
  staticClasses,
} from "@decky/ui";
import { useCallback, useEffect, useRef, useState } from "react";

import {
  acknowledgeDockedIgpuStatus,
  getSnapshot,
  getPeripheralStatus,
  getActionHistory,
  acknowledgeProcessRelease,
  approveProcessRelease,
  approvePresentationPreparation,
  executeProcessRelease,
  getProcessReleaseStatus,
  getDockedIgpuStatus,
  getDiagnosticLoggingStatus,
  enableDiagnosticLogging,
  disableDiagnosticLogging,
  preparePresentationIntegration,
  previewPresentationPreparation,
  previewProcessRelease,
  previewSupportBundle,
  saveSupportBundle,
  type SnapshotPayload,
  type DockedIgpuStatusPayload,
  type DiagnosticLoggingDuration,
  type DiagnosticLoggingStatusPayload,
  type PeripheralStatusPayload,
  type ActionHistoryPayload,
  type ProcessReleasePhase,
  type ProcessReleasePreviewPayload,
  type SupportBundlePreviewPayload,
} from "./backend";
import { createDeckySteamSuspendAdapter } from "./decky-steam-suspend";
import { deliverBlockedAttempt } from "./blocked-attempt-delivery";
import { diagnosticOverlayRows } from "./diagnostics-overlay";
import { healthStatusLabel } from "./health-ui";
import { collectOptionalDiagnostics } from "./optional-diagnostics-refresh";
import { connectionProgress, refreshDelayForSnapshot } from "./refresh-policy";
import { canOfferForce, processReleaseOutcomeMessage } from "./process-release-ui";
import {
  SleepPreflightCoordinator,
  observationFromSnapshotEvidence,
  type BlockedAttemptWarning,
  type PreflightObservation,
} from "./sleep-preflight";


const LABELS: Record<string, string> = {
  boosted_handheld: "Boosted Handheld",
  certified: "Certified",
  degraded: "Degraded",
  experimental: "Experimental",
  game: "Game",
  idle: "No game running",
  portable: "Portable",
  running: "Game running",
  protected: "Protected",
  system: "System",
  tv_docked: "TV Docked",
  unknown: "Unknown",
  unsupported: "Unsupported",
  user: "User",
};

const SLEEP_WARNING_KEY = "hdm.hideAttachedG1SleepWarning";
const SNAPSHOT_STALE_AFTER_MS = 10_000;
const BLOCKED_ATTEMPT_MODAL_DELAY_MS = 750;
const DIAGNOSTIC_LOGGING_OPTIONS = [
  { data: "30_minutes", label: "30 minutes" },
  { data: "1_hour", label: "1 hour" },
  { data: "2_hours", label: "2 hours" },
  { data: "until_reboot", label: "Until reboot" },
] satisfies Array<{ data: DiagnosticLoggingDuration; label: string }>;

function label(value: string): string {
  return LABELS[value] ?? value.replaceAll("_", " ").replaceAll(".", " ");
}

function DiagnosticRow({ name, value }: { name: string; value: string }) {
  return (
    <PanelSectionRow>
      <div style={{ display: "flex", justifyContent: "space-between", gap: "12px", width: "100%" }}>
        <span>{name}</span>
        <span style={{ opacity: 0.72, textAlign: "right" }}>{value}</span>
      </div>
    </PanelSectionRow>
  );
}

function showSupportBundlePreview(
  preview: SupportBundlePreviewPayload,
  onClose: () => void,
): ReturnType<typeof showModal> {
  let modal: ReturnType<typeof showModal>;
  const close = () => {
    modal.Close();
    onClose();
  };
  // Let Decky resolve Steam's visible SP window. This plugin executes in the
  // invisible SharedJSContext, so using its global window hides the dialog.
  modal = showModal(
    <ConfirmModal
      strTitle="Redacted support bundle preview"
      strOKButtonText="Close preview"
      bAlertDialog={true}
      bDisableBackgroundDismiss={true}
      bHideCloseIcon={true}
      onOK={close}
    >
      <div style={{ fontSize: "12px", lineHeight: "17px" }}>
        <p>
          Review this exact redacted JSON before copying or saving it. The save approval expires
          after five minutes and can be used once.
        </p>
        <div style={{ maxHeight: "55vh", overflow: "hidden" }}>
          <ScrollPanel>
            <pre style={{ whiteSpace: "pre-wrap" }}>{preview.preview_json}</pre>
          </ScrollPanel>
        </div>
      </div>
    </ConfirmModal>,
    undefined,
    { strTitle: "Handheld Dock Mode", bNeverPopOut: true },
  );
  return modal;
}

function showPresentationPreparationConfirmation(
  onConfirm: () => void,
  onClose: () => void,
): ReturnType<typeof showModal> {
  let modal: ReturnType<typeof showModal>;
  const close = () => {
    modal.Close();
    onClose();
  };
  modal = showModal(
    <ConfirmModal
      strTitle="Prepare experimental display validation?"
      strOKButtonText="Prepare"
      strCancelButtonText="Cancel"
      bDestructiveWarning={true}
      bDisableBackgroundDismiss={true}
      bHideCloseIcon={true}
      onOK={() => {
        close();
        onConfirm();
      }}
      onCancel={close}
    >
      <div style={{ fontSize: "13px", lineHeight: "18px" }}>
        <p>
          Continue only with the G1 disconnected, no game running, and the Ally screen visible.
        </p>
        <p>
          This installs HDM&apos;s reversible Gamescope startup integration and reloads the user
          service configuration. It does not restart Gamescope, switch displays, or select a GPU.
        </p>
      </div>
    </ConfirmModal>,
    undefined,
    { strTitle: "Handheld Dock Mode", bNeverPopOut: true },
  );
  return modal;
}

function showProcessReleaseConfirmation(
  preview: ProcessReleasePreviewPayload,
  onConfirm: () => void,
  onClose: () => void,
): ReturnType<typeof showModal> {
  let modal: ReturnType<typeof showModal>;
  const force = preview.phase === "force";
  const close = () => {
    modal.Close();
    onClose();
  };
  modal = showModal(
    <ConfirmModal
      strTitle={force ? "Force close eGPU processes?" : "Close eGPU processes?"}
      strOKButtonText={force ? "Force close" : "Close gracefully"}
      strCancelButtonText="Cancel"
      bDestructiveWarning={true}
      bDisableBackgroundDismiss={true}
      bHideCloseIcon={true}
      onOK={() => {
        close();
        onConfirm();
      }}
      onCancel={close}
    >
      <div style={{ fontSize: "13px", lineHeight: "18px" }}>
        <p>
          {force
            ? "Force close may lose unsaved work. Only the exact processes that survived the approved graceful attempt are eligible."
            : "HDM will request a graceful close only for the exact ordinary user processes listed below."}
        </p>
        {preview.targets.map((target, index) => (
          <p key={`${target.name}-${index}`}>
            {target.name} — {target.resources.map(label).join(", ")}
          </p>
        ))}
        {preview.protected_client_count > 0 && (
          <p>{preview.protected_client_count} protected client(s) will not be closed.</p>
        )}
        <p>
          Clearing software clients does not authorize physical G1 removal. Shut down before
          disconnecting the G1.
        </p>
      </div>
    </ConfirmModal>,
    undefined,
    { strTitle: "Handheld Dock Mode", bNeverPopOut: true },
  );
  return modal;
}

function showDiagnosticLoggingConfirmation(
  durationLabel: string,
  onConfirm: () => void,
  onClose: () => void,
): ReturnType<typeof showModal> {
  let modal: ReturnType<typeof showModal>;
  const close = () => {
    modal.Close();
    onClose();
  };
  modal = showModal(
    <ConfirmModal
      strTitle="Enable verbose HDM diagnostics?"
      strOKButtonText="Enable"
      strCancelButtonText="Cancel"
      bDisableBackgroundDismiss={true}
      bHideCloseIcon={true}
      onOK={() => {
        close();
        onConfirm();
      }}
      onCancel={close}
    >
      <div style={{ fontSize: "13px", lineHeight: "18px" }}>
        <p>
          HDM will retain additional sanitized, HDM-only events for {durationLabel}.
          Storage remains capped and verbose logging will not survive a reboot.
        </p>
        <p>
          Logs stay on this handheld unless you separately preview, save, and share a
          support bundle.
        </p>
      </div>
    </ConfirmModal>,
    undefined,
    { strTitle: "Handheld Dock Mode", bNeverPopOut: true },
  );
  return modal;
}

function MonitorIcon() {
  return (
    <svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <rect x="3" y="4" width="18" height="13" rx="2" />
      <path d="M8 21h8M12 17v4" />
    </svg>
  );
}

function preflightObservation(payload: SnapshotPayload): PreflightObservation {
  const { snapshot } = payload;
  return observationFromSnapshotEvidence({
    schemaVersion: snapshot.schema_version,
    observedAt: snapshot.observed_at,
    guardRequired: snapshot.sleep_guard.required,
    guardConfidence: snapshot.sleep_guard.confidence,
    gameState: snapshot.game_state,
    gameUsesEgpu: snapshot.disconnect_readiness.clients.some(
      (client) => client.kind === "game",
    ),
  }, Date.now(), SNAPSHOT_STALE_AFTER_MS);
}

function Content({ preflight }: { preflight: SleepPreflightCoordinator }) {
  const [payload, setPayload] = useState<SnapshotPayload | null>(null);
  const [peripheralStatus, setPeripheralStatus] = useState<PeripheralStatusPayload | null>(null);
  const [actionHistory, setActionHistory] = useState<ActionHistoryPayload | null>(null);
  const [dockedIgpuStatus, setDockedIgpuStatus] = useState<DockedIgpuStatusPayload | null>(null);
  const [dockedIgpuMessage, setDockedIgpuMessage] = useState("");
  const [diagnosticLoggingStatus, setDiagnosticLoggingStatus] = useState<DiagnosticLoggingStatusPayload | null>(null);
  const [diagnosticLoggingDuration, setDiagnosticLoggingDuration] = useState<DiagnosticLoggingDuration>("2_hours");
  const [diagnosticLoggingBusy, setDiagnosticLoggingBusy] = useState(false);
  const [diagnosticLoggingMessage, setDiagnosticLoggingMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [preflightStatus, setPreflightStatus] = useState(() => preflight.status());
  const [sleepWarningHidden, setSleepWarningHidden] = useState(
    () => localStorage.getItem(SLEEP_WARNING_KEY) === "1",
  );
  const [supportPreview, setSupportPreview] = useState<SupportBundlePreviewPayload | null>(null);
  const [supportBusy, setSupportBusy] = useState(false);
  const [supportMessage, setSupportMessage] = useState("");
  const [showDiagnostics, setShowDiagnostics] = useState(false);
  const [presentationBusy, setPresentationBusy] = useState(false);
  const [presentationMessage, setPresentationMessage] = useState("");
  const [processBusy, setProcessBusy] = useState(false);
  const [processMessage, setProcessMessage] = useState("");
  const [processAcknowledgementId, setProcessAcknowledgementId] = useState("");
  const [forceReceiptToken, setForceReceiptToken] = useState("");
  const lastSnapshotAt = useRef<number | null>(null);
  const refreshInFlight = useRef(false);
  const warningToastShown = useRef(false);
  const inactiveToastShown = useRef(false);
  const supportModal = useRef<ReturnType<typeof showModal> | null>(null);
  const presentationModal = useRef<ReturnType<typeof showModal> | null>(null);
  const processModal = useRef<ReturnType<typeof showModal> | null>(null);
  const diagnosticLoggingModal = useRef<ReturnType<typeof showModal> | null>(null);

  useEffect(() => () => {
    supportModal.current?.Close();
    supportModal.current = null;
    presentationModal.current?.Close();
    presentationModal.current = null;
    processModal.current?.Close();
    processModal.current = null;
    diagnosticLoggingModal.current?.Close();
    diagnosticLoggingModal.current = null;
  }, []);

  useEffect(() => {
    let disposed = false;
    void getProcessReleaseStatus().then((status) => {
      if (disposed || status.code === "process_release.idle") {
        return;
      }
      if (status.acknowledgement_required && status.acknowledgement_id) {
        setProcessAcknowledgementId(status.acknowledgement_id);
      }
      setProcessMessage(
        status.action_required
          ? "A prior process-release attempt needs acknowledgement. Do not disconnect the G1."
          : `Previous process-release result: ${label(status.code)}.`,
      );
    }).catch(() => {
      if (!disposed) {
        setProcessMessage("Process-release safety state is unavailable. Do not disconnect the G1.");
      }
    });
    return () => {
      disposed = true;
    };
  }, []);

  const refresh = useCallback(async (quiet = false): Promise<SnapshotPayload | null> => {
    if (refreshInFlight.current) {
      return null;
    }
    refreshInFlight.current = true;
    if (!quiet) {
      setLoading(true);
      setError("");
    }
    try {
      const [nextPayload, optionalDiagnostics] = await Promise.all([
        getSnapshot(),
        collectOptionalDiagnostics(showDiagnostics, {
          getDockedIgpuStatus,
          getDiagnosticLoggingStatus,
          getPeripheralStatus,
          getActionHistory,
        }),
      ]);
      setPayload(nextPayload);
      setDockedIgpuStatus(optionalDiagnostics.dockedIgpuStatus);
      setDiagnosticLoggingStatus(optionalDiagnostics.diagnosticLoggingStatus);
      setPeripheralStatus(optionalDiagnostics.peripheralStatus);
      setActionHistory(optionalDiagnostics.actionHistory);
      setError("");
      lastSnapshotAt.current = Date.now();
      setPreflightStatus(preflight.reconcile(preflightObservation(nextPayload)));
      return nextPayload;
    } catch {
      setError("Read-only snapshot unavailable. Check the Decky log for details.");
      setPreflightStatus(preflight.reconcile({ kind: "unavailable" }));
      return null;
    } finally {
      refreshInFlight.current = false;
      if (!quiet) {
        setLoading(false);
      }
    }
  }, [preflight, showDiagnostics]);

  useEffect(() => {
    let disposed = false;
    let timer: number | null = null;
    const poll = async (quiet: boolean) => {
      if (
        lastSnapshotAt.current !== null
        && Date.now() - lastSnapshotAt.current > SNAPSHOT_STALE_AFTER_MS
      ) {
        setPreflightStatus(preflight.reconcile({ kind: "stale" }));
      }
      const nextPayload = await refresh(quiet);
      if (!disposed) {
        timer = window.setTimeout(
          () => void poll(true),
          refreshDelayForSnapshot(nextPayload),
        );
      }
    };
    void poll(false);
    return () => {
      disposed = true;
      if (timer !== null) {
        window.clearTimeout(timer);
      }
    };
  }, [preflight, refresh]);

  const snapshot = payload?.snapshot;
  const renderer = snapshot?.gpus.find((gpu) => gpu.selected_for_render === true);
  const display = snapshot?.displays.find((item) => item.active === true);
  const disconnect = snapshot?.disconnect_readiness;
  const sleepGuard = snapshot?.sleep_guard;
  const progress = connectionProgress(payload);
  const totalTiming = payload?.diagnostics.timings_ms.find(
    (timing) => timing.stage === "snapshot_total",
  );
  const gameUsesEgpu = disconnect?.clients.some((client) => client.kind === "game") ?? false;
  const closeEligibleClientCount = disconnect?.clients.filter(
    (client) => client.kind === "user" && client.close_eligible,
  ).length ?? 0;
  const disconnectStatus = loading
    ? "Reading…"
    : !disconnect?.applicable
      ? "eGPU not connected"
      : !disconnect.scan_complete
        ? "Scan incomplete — blocked"
        : disconnect.ready
          ? "Ready"
          : "Blocked";
  const overlayRows = diagnosticOverlayRows(
    payload,
    dockedIgpuStatus,
    diagnosticLoggingStatus,
    peripheralStatus,
    actionHistory,
  );

  const acknowledgeDockedIgpuWatch = useCallback(async () => {
    setDockedIgpuMessage("");
    try {
      const result = await acknowledgeDockedIgpuStatus();
      if (!result.acknowledged) {
        setDockedIgpuMessage("The watcher state could not be acknowledged.");
        return;
      }
      const status = await getDockedIgpuStatus();
      setDockedIgpuStatus(status);
      setDockedIgpuMessage("Watcher state acknowledged. Observation will resume.");
    } catch {
      setDockedIgpuMessage("Watcher acknowledgement is unavailable.");
    }
  }, []);

  const applyDiagnosticLogging = useCallback(async () => {
    setDiagnosticLoggingBusy(true);
    setDiagnosticLoggingMessage("");
    try {
      const status = await enableDiagnosticLogging(
        diagnosticLoggingDuration,
        true,
      );
      setDiagnosticLoggingStatus(status);
      setDiagnosticLoggingMessage(
        status.enabled
          ? "Verbose diagnostics enabled. They remain local until separately exported."
          : "Verbose diagnostics were not enabled.",
      );
    } catch {
      setDiagnosticLoggingMessage("Verbose diagnostics could not be enabled.");
    } finally {
      setDiagnosticLoggingBusy(false);
    }
  }, [diagnosticLoggingDuration]);

  const requestDiagnosticLogging = useCallback(() => {
    const option = DIAGNOSTIC_LOGGING_OPTIONS.find(
      (value) => value.data === diagnosticLoggingDuration,
    );
    diagnosticLoggingModal.current?.Close();
    diagnosticLoggingModal.current = showDiagnosticLoggingConfirmation(
      option?.label ?? "the selected duration",
      () => void applyDiagnosticLogging(),
      () => {
        diagnosticLoggingModal.current = null;
      },
    );
  }, [applyDiagnosticLogging, diagnosticLoggingDuration]);

  const stopDiagnosticLogging = useCallback(async () => {
    setDiagnosticLoggingBusy(true);
    setDiagnosticLoggingMessage("");
    try {
      const status = await disableDiagnosticLogging();
      setDiagnosticLoggingStatus(status);
      setDiagnosticLoggingMessage("Verbose diagnostics disabled.");
    } catch {
      setDiagnosticLoggingMessage("Verbose diagnostics status is unavailable.");
    } finally {
      setDiagnosticLoggingBusy(false);
    }
  }, []);

  useEffect(() => {
    if (!sleepGuard?.required) {
      warningToastShown.current = false;
      inactiveToastShown.current = false;
      return;
    }
    if (sleepGuard.active) {
      inactiveToastShown.current = false;
    } else if (!inactiveToastShown.current) {
      toaster.toast({
        title: "G1 sleep protection is inactive",
        body: sleepGuard.error || "Do not put the handheld to sleep while the G1 is attached.",
        critical: true,
        duration: 10000,
      });
      inactiveToastShown.current = true;
    }
    if (!sleepWarningHidden && !warningToastShown.current) {
      toaster.toast({
        title: gameUsesEgpu ? "Sleep blocked while game uses G1" : "Sleep blocked while G1 is attached",
        body: "This hardware is known to wake immediately after sleep. Restore Portable and disconnect only after shutdown.",
        duration: 10000,
      });
      warningToastShown.current = true;
    }
  }, [gameUsesEgpu, sleepGuard, sleepWarningHidden]);

  const hideSleepWarning = useCallback(() => {
    localStorage.setItem(SLEEP_WARNING_KEY, "1");
    setSleepWarningHidden(true);
  }, []);

  const showSleepWarning = useCallback(() => {
    localStorage.removeItem(SLEEP_WARNING_KEY);
    warningToastShown.current = false;
    setSleepWarningHidden(false);
  }, []);

  const createSupportPreview = useCallback(async () => {
    setSupportBusy(true);
    setSupportMessage("");
    try {
      const preview = await previewSupportBundle();
      setSupportPreview(preview);
      setSupportMessage("Redacted preview ready. Review it before copying or saving.");
      supportModal.current?.Close();
      supportModal.current = showSupportBundlePreview(preview, () => {
        supportModal.current = null;
      });
    } catch {
      setSupportMessage("Support bundle preview failed. No file was written.");
    } finally {
      setSupportBusy(false);
    }
  }, []);

  const reviewSupportPreview = useCallback(() => {
    if (!supportPreview) {
      return;
    }
    supportModal.current?.Close();
    supportModal.current = showSupportBundlePreview(supportPreview, () => {
      supportModal.current = null;
    });
  }, [supportPreview]);

  const copySupportPreview = useCallback(async () => {
    if (!supportPreview) {
      return;
    }
    setSupportBusy(true);
    try {
      if (!navigator.clipboard?.writeText) {
        throw new Error("clipboard unavailable");
      }
      await navigator.clipboard.writeText(supportPreview.preview_json);
      setSupportMessage("Redacted support bundle copied to the clipboard.");
    } catch {
      setSupportMessage("Clipboard copy is unavailable. The preview was not changed.");
    } finally {
      setSupportBusy(false);
    }
  }, [supportPreview]);

  const saveApprovedSupportPreview = useCallback(async () => {
    if (!supportPreview) {
      return;
    }
    setSupportBusy(true);
    try {
      const result = await saveSupportBundle(supportPreview.preview_token);
      setSupportMessage(
        result.ok
          ? `Saved the reviewed bundle to ${result.relative_path}.`
          : "Support bundle save did not complete.",
      );
      if (result.ok) {
        setSupportPreview(null);
      }
    } catch {
      setSupportMessage("Save approval expired or failed. Create and review a new preview.");
      setSupportPreview(null);
    } finally {
      setSupportBusy(false);
    }
  }, [supportPreview]);

  const preparePresentation = useCallback(async () => {
    setPresentationBusy(true);
    setPresentationMessage("");
    try {
      const approval = await approvePresentationPreparation();
      if (!approval.approval_token || approval.blockers.length > 0) {
        setPresentationMessage(
          approval.blockers.length > 0
            ? `Preparation blocked: ${approval.blockers.map(label).join(", ")}.`
            : "Preparation approval was not issued. Inspect again.",
        );
        return;
      }
      const outcome = await preparePresentationIntegration(approval.approval_token);
      setPresentationMessage(
        outcome.prepared
          ? outcome.changed
            ? "Gamescope validation integration prepared. Gamescope was not restarted."
            : "Gamescope validation integration was already prepared."
          : outcome.rollback_attempted && !outcome.rollback_succeeded
            ? "Preparation failed and rollback needs attention. Do not restart Gamescope."
            : `Preparation did not complete: ${label(outcome.code)}.`,
      );
    } catch {
      setPresentationMessage("Preparation failed safely. Gamescope was not intentionally restarted.");
    } finally {
      setPresentationBusy(false);
    }
  }, []);

  const inspectPresentationPreparation = useCallback(async () => {
    setPresentationBusy(true);
    setPresentationMessage("");
    try {
      const preview = await previewPresentationPreparation();
      if (preview.blockers.length > 0) {
        setPresentationMessage(
          `Preparation blocked: ${preview.blockers.map(label).join(", ")}.`,
        );
        return;
      }
      if (preview.ready) {
        setPresentationMessage("Gamescope validation integration is already prepared.");
        return;
      }
      presentationModal.current?.Close();
      presentationModal.current = showPresentationPreparationConfirmation(
        () => void preparePresentation(),
        () => {
          presentationModal.current = null;
        },
      );
    } catch {
      setPresentationMessage("Preparation inspection is unavailable. No change was made.");
    } finally {
      setPresentationBusy(false);
    }
  }, [preparePresentation]);

  const runProcessRelease = useCallback(async (
    phase: ProcessReleasePhase,
    receiptToken: string,
  ) => {
    setProcessBusy(true);
    setProcessMessage("");
    try {
      const approval = await approveProcessRelease(phase, receiptToken);
      if (!approval.approval_token || approval.blockers.length > 0) {
        setProcessMessage(
          approval.blockers.length > 0
            ? `Process release blocked: ${approval.blockers.map(label).join(", ")}.`
            : "Process-release approval was not issued. Inspect again.",
        );
        if (phase === "force") {
          setForceReceiptToken("");
        }
        return;
      }
      const outcome = await executeProcessRelease(approval.approval_token);
      setProcessMessage(processReleaseOutcomeMessage(outcome));
      setProcessAcknowledgementId(outcome.acknowledgement_id);
      setForceReceiptToken(canOfferForce(outcome) ? outcome.force_receipt_token : "");
      await refresh(true);
    } catch {
      setProcessMessage("Process release failed closed. Do not disconnect the G1.");
      if (phase === "force") {
        setForceReceiptToken("");
      }
    } finally {
      setProcessBusy(false);
    }
  }, [refresh]);

  const inspectProcessRelease = useCallback(async (
    phase: ProcessReleasePhase,
    receiptToken = "",
  ) => {
    setProcessBusy(true);
    setProcessMessage("");
    try {
      const preview = await previewProcessRelease(phase, receiptToken);
      if (!preview.ready || preview.blockers.length > 0 || preview.targets.length === 0) {
        setProcessMessage(
          preview.blockers.length > 0
            ? `Process release blocked: ${preview.blockers.map(label).join(", ")}.`
            : "No eligible ordinary user process is holding the G1.",
        );
        return;
      }
      processModal.current?.Close();
      processModal.current = showProcessReleaseConfirmation(
        preview,
        () => void runProcessRelease(phase, receiptToken),
        () => {
          processModal.current = null;
        },
      );
    } catch {
      setProcessMessage("Process-release inspection is unavailable. No process was signaled.");
    } finally {
      setProcessBusy(false);
    }
  }, [runProcessRelease]);

  const acknowledgeProcessResult = useCallback(async () => {
    if (!processAcknowledgementId) {
      return;
    }
    setProcessBusy(true);
    try {
      const result = await acknowledgeProcessRelease(processAcknowledgementId);
      if (!result.acknowledged) {
        setProcessMessage("The exact process-release result could not be acknowledged.");
        return;
      }
      setProcessAcknowledgementId("");
      setForceReceiptToken("");
      setProcessMessage("Process-release result acknowledged. Inspect again if blockers remain.");
    } catch {
      setProcessMessage("Process-release acknowledgement failed.");
    } finally {
      setProcessBusy(false);
    }
  }, [processAcknowledgementId]);

  const reviewForceClose = useCallback(async () => {
    if (!forceReceiptToken) {
      return;
    }
    setProcessBusy(true);
    try {
      if (processAcknowledgementId) {
        const result = await acknowledgeProcessRelease(processAcknowledgementId);
        if (!result.acknowledged) {
          setProcessMessage("Acknowledge the graceful result before force-close review.");
          return;
        }
        setProcessAcknowledgementId("");
      }
      await inspectProcessRelease("force", forceReceiptToken);
    } catch {
      setProcessMessage("Force-close review is unavailable. No process was signaled.");
    } finally {
      setProcessBusy(false);
    }
  }, [forceReceiptToken, inspectProcessRelease, processAcknowledgementId]);

  return (
    <>
      <PanelSection title="Observed state">
        <DiagnosticRow name="Connection" value={progress.label} />
        <DiagnosticRow name="Mode" value={loading ? "Reading…" : label(payload?.inference.mode ?? "unknown")} />
        <DiagnosticRow name="System health" value={healthStatusLabel(payload?.health, loading)} />
        <DiagnosticRow name="Game" value={label(snapshot?.game_state ?? "unknown")} />
        <DiagnosticRow name="Render GPU" value={renderer ? label(renderer.role) : "Unknown"} />
        <DiagnosticRow name="Active display" value={display ? label(display.kind) : "Unknown"} />
        <DiagnosticRow name="Hardware" value={label(snapshot?.support_tier ?? "unknown")} />
        <DiagnosticRow
          name="Snapshot time"
          value={totalTiming ? `${Math.round(totalTiming.duration_ms)} ms` : "Unknown"}
        />
        <PanelSectionRow>{progress.detail}</PanelSectionRow>
      </PanelSection>

      <PanelSection title="Sleep protection">
        <DiagnosticRow
          name="System inhibitor"
          value={loading
            ? "Checking…"
            : sleepGuard?.required
              ? sleepGuard.active
                ? "Active"
                : "Inactive"
              : "Not required"}
        />
        <DiagnosticRow
          name="Steam preflight"
          value={preflightStatus.state === "active"
            ? preflightStatus.attemptWarningAvailable
              ? "Active"
              : "Blocked; warning unavailable"
            : preflightStatus.state === "inactive"
              ? "Standby — G1 verified absent"
              : "Unavailable"}
        />
        {preflightStatus.error && (
          <PanelSectionRow>{preflightStatus.error}</PanelSectionRow>
        )}
        {sleepGuard?.required && (
          <>
            {!sleepWarningHidden && (
              <>
                <PanelSectionRow>
                  {gameUsesEgpu
                    ? "A game is using the G1. Sleep is blocked to prevent the known immediate-wake behavior and workload risk."
                    : "The attached G1 is known to wake this handheld immediately after sleep. Sleep remains blocked until the G1 is verified absent."}
                </PanelSectionRow>
                <PanelSectionRow>
                  <ButtonItem layout="below" onClick={hideSleepWarning}>
                    Never show this explanation again
                  </ButtonItem>
                </PanelSectionRow>
              </>
            )}
            {sleepWarningHidden && (
              <PanelSectionRow>
                The explanation is hidden. Sleep protection remains active.
              </PanelSectionRow>
            )}
          </>
        )}
      </PanelSection>

      <PanelSection title="Disconnect readiness">
        <DiagnosticRow name="Status" value={disconnectStatus} />
        {disconnect?.applicable && (
          <DiagnosticRow
            name="Resource clients"
            value={String(disconnect.clients.length)}
          />
        )}
        {(disconnect?.storage_devices ?? 0) > 0 && (
          <DiagnosticRow
            name="eGPU storage"
            value={disconnect?.storage_in_use ? "In use — blocked" : "Not mounted"}
          />
        )}
        {disconnect?.error && <PanelSectionRow>{disconnect.error}</PanelSectionRow>}
        {closeEligibleClientCount > 0 && !processAcknowledgementId && (
          <PanelSectionRow>
            <ButtonItem
              layout="below"
              onClick={() => void inspectProcessRelease("graceful")}
              disabled={processBusy}
            >
              {processBusy ? "Checking…" : "Close eligible eGPU processes"}
            </ButtonItem>
          </PanelSectionRow>
        )}
        {forceReceiptToken && (
          <PanelSectionRow>
            <ButtonItem
              layout="below"
              onClick={() => void reviewForceClose()}
              disabled={processBusy}
            >
              Review force close
            </ButtonItem>
          </PanelSectionRow>
        )}
        {processAcknowledgementId && !forceReceiptToken && (
          <PanelSectionRow>
            <ButtonItem
              layout="below"
              onClick={() => void acknowledgeProcessResult()}
              disabled={processBusy}
            >
              Acknowledge process-release result
            </ButtonItem>
          </PanelSectionRow>
        )}
        {processMessage && <PanelSectionRow>{processMessage}</PanelSectionRow>}
        <PanelSectionRow>
          Process closure always requires confirmation. Software readiness never authorizes
          physical G1 removal.
        </PanelSectionRow>
      </PanelSection>

      {(error || (snapshot?.blockers.length ?? 0) > 0) && (
        <PanelSection title="Needs attention">
          {error && <PanelSectionRow>{error}</PanelSectionRow>}
          {snapshot?.blockers.map((blocker) => (
            <PanelSectionRow key={blocker.code}>{blocker.message}</PanelSectionRow>
          ))}
        </PanelSection>
      )}

      <PanelSection title="Support bundle">
        <PanelSectionRow>
          Preview a bounded HDM-only report before copying or saving it. Raw hardware IDs,
          addresses, usernames, home paths, and command lines are excluded or redacted.
        </PanelSectionRow>
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={() => void createSupportPreview()} disabled={supportBusy}>
            {supportBusy ? "Working…" : "Preview redacted support bundle"}
          </ButtonItem>
        </PanelSectionRow>
        {supportPreview && (
          <>
            <DiagnosticRow name="Preview size" value={`${supportPreview.size_bytes} bytes`} />
            <DiagnosticRow name="Recent events" value={String(supportPreview.event_count)} />
            <PanelSectionRow>
              <ButtonItem layout="below" onClick={reviewSupportPreview} disabled={supportBusy}>
                Review exact redacted JSON
              </ButtonItem>
            </PanelSectionRow>
            <PanelSectionRow>
              <ButtonItem layout="below" onClick={() => void copySupportPreview()} disabled={supportBusy}>
                Copy reviewed JSON
              </ButtonItem>
            </PanelSectionRow>
            <PanelSectionRow>
              <ButtonItem
                layout="below"
                onClick={() => void saveApprovedSupportPreview()}
                disabled={supportBusy}
              >
                Save reviewed bundle to Downloads
              </ButtonItem>
            </PanelSectionRow>
          </>
        )}
        {supportMessage && <PanelSectionRow>{supportMessage}</PanelSectionRow>}
      </PanelSection>

      <PanelSection title="Diagnostics only">
        <PanelSectionRow>
          HDM 0.2 observes state and blocks sleep while the G1 is attached. It cannot switch displays, GPUs, or Gamescope. It can close only exact eligible eGPU processes after explicit approval.
        </PanelSectionRow>
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={() => void refresh()} disabled={loading}>
            {loading ? "Reading…" : "Refresh"}
          </ButtonItem>
        </PanelSectionRow>
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={() => setShowDiagnostics((value) => !value)}>
            {showDiagnostics ? "Hide troubleshooting details" : "Show troubleshooting details"}
          </ButtonItem>
        </PanelSectionRow>
        {sleepGuard?.required && sleepWarningHidden && (
          <PanelSectionRow>
            <ButtonItem layout="below" onClick={showSleepWarning}>
              Show sleep warning again
            </ButtonItem>
          </PanelSectionRow>
        )}
      </PanelSection>

      {showDiagnostics && (
        <PanelSection title="Troubleshooting details">
          <PanelSectionRow>
            Read-only technical evidence. Raw hardware identities, connector names, and process IDs are hidden.
          </PanelSectionRow>
          {overlayRows.map((row) => (
            <DiagnosticRow key={row.name} name={row.name} value={row.value} />
          ))}
          {dockedIgpuStatus?.acknowledgement_required && (
            <PanelSectionRow>
              <ButtonItem
                layout="below"
                onClick={() => void acknowledgeDockedIgpuWatch()}
              >
                Acknowledge Docked-iGPU watcher state
              </ButtonItem>
            </PanelSectionRow>
          )}
          {dockedIgpuMessage && (
            <PanelSectionRow>{dockedIgpuMessage}</PanelSectionRow>
          )}
          <DropdownItem
            label="Verbose logging duration"
            description="Temporary, sanitized, capped, and off by default"
            rgOptions={DIAGNOSTIC_LOGGING_OPTIONS}
            selectedOption={diagnosticLoggingDuration}
            disabled={diagnosticLoggingBusy || diagnosticLoggingStatus?.enabled === true}
            onChange={(option) => {
              setDiagnosticLoggingDuration(option.data as DiagnosticLoggingDuration);
            }}
          />
          <PanelSectionRow>
            <ButtonItem
              layout="below"
              onClick={diagnosticLoggingStatus?.enabled
                ? () => void stopDiagnosticLogging()
                : requestDiagnosticLogging}
              disabled={diagnosticLoggingBusy}
            >
              {diagnosticLoggingStatus?.enabled
                ? "Disable verbose diagnostics"
                : "Enable verbose diagnostics"}
            </ButtonItem>
          </PanelSectionRow>
          {diagnosticLoggingMessage && (
            <PanelSectionRow>{diagnosticLoggingMessage}</PanelSectionRow>
          )}
          <PanelSectionRow>
            <ButtonItem
              layout="below"
              onClick={() => void inspectPresentationPreparation()}
              disabled={presentationBusy}
            >
              {presentationBusy ? "Checking…" : "Prepare supervised display validation"}
            </ButtonItem>
          </PanelSectionRow>
          <PanelSectionRow>
            Preparation only. This control cannot restart Gamescope or switch displays.
          </PanelSectionRow>
          {presentationMessage && <PanelSectionRow>{presentationMessage}</PanelSectionRow>}
        </PanelSection>
      )}
    </>
  );
}

function showBlockedAttempt(
  warning: BlockedAttemptWarning,
  onClose: () => void,
): ReturnType<typeof showModal> {
  let modal: ReturnType<typeof showModal>;
  const close = () => {
    modal.Close();
    onClose();
  };
  // Let Decky resolve Steam's visible SP window after the Power menu closes.
  // SharedJSContext's global window is not a player-visible modal parent.
  modal = showModal(
    <ConfirmModal
      strTitle={warning.title}
      strDescription={warning.body}
      strOKButtonText="OK"
      bAlertDialog={true}
      bDestructiveWarning={warning.critical}
      bDisableBackgroundDismiss={true}
      bHideCloseIcon={true}
      onOK={close}
    />,
    undefined,
    { strTitle: "Handheld Dock Mode", bNeverPopOut: true },
  );
  return modal;
}

export default definePlugin(() => {
  let warningModal: ReturnType<typeof showModal> | null = null;
  let warningTimer: number | null = null;
  const preflight = new SleepPreflightCoordinator(
    createDeckySteamSuspendAdapter(),
    (warning) => {
      if (warningTimer !== null) {
        window.clearTimeout(warningTimer);
      }
      warningModal?.Close();
      warningModal = null;
      // Steam closes the Power menu after dispatching OnSuspendRequest. Defer the
      // acknowledgement dialog so it is not discarded with that transient menu.
      warningTimer = window.setTimeout(() => {
        warningTimer = null;
        deliverBlockedAttempt(warning, {
          showModal: () => {
            warningModal = showBlockedAttempt(warning, () => {
              warningModal = null;
            });
          },
          showFallbackToast: (fallback) => {
            toaster.toast({
              title: fallback.title,
              body: fallback.body,
              critical: true,
              duration: 15000,
            });
          },
        });
      }, BLOCKED_ATTEMPT_MODAL_DELAY_MS);
    },
  );
  preflight.start();

  return {
    name: "Handheld Dock Mode",
    titleView: <div className={staticClasses.Title}>Handheld Dock Mode</div>,
    content: <Content preflight={preflight} />,
    icon: <MonitorIcon />,
    alwaysRender: true,
    onDismount() {
      if (warningTimer !== null) {
        window.clearTimeout(warningTimer);
        warningTimer = null;
      }
      warningModal?.Close();
      warningModal = null;
      preflight.stop();
    },
  };
});
