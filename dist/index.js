const manifest = {"name":"Handheld Dock Mode"};
const API_VERSION = 2;
const internalAPIConnection = window.__DECKY_SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED_deckyLoaderAPIInit;
if (!internalAPIConnection) {
    throw new Error('[@decky/api]: Failed to connect to the loader as as the loader API was not initialized. This is likely a bug in Decky Loader.');
}
let api;
try {
    api = internalAPIConnection.connect(API_VERSION, manifest.name);
}
catch {
    api = internalAPIConnection.connect(1, manifest.name);
    console.warn(`[@decky/api] Requested API version ${API_VERSION} but the running loader only supports version 1. Some features may not work.`);
}
if (api._version != API_VERSION) {
    console.warn(`[@decky/api] Requested API version ${API_VERSION} but the running loader only supports version ${api._version}. Some features may not work.`);
}
const callable = api.callable;
const toaster = api.toaster;
const definePlugin = (fn) => {
    return (...args) => {
        return fn(...args);
    };
};

const getSnapshot = callable("get_snapshot");
const getPeripheralStatus = callable("get_peripheral_status");
const getDockedIgpuStatus = callable("get_docked_igpu_status");
const acknowledgeDockedIgpuStatus = callable("acknowledge_docked_igpu_status");
const getDiagnosticLoggingStatus = callable("get_diagnostic_logging_status");
const enableDiagnosticLogging = callable("enable_diagnostic_logging");
const disableDiagnosticLogging = callable("disable_diagnostic_logging");
const previewSupportBundle = callable("preview_support_bundle");
const saveSupportBundle = callable("save_support_bundle");
const previewPresentationPreparation = callable("preview_presentation_preparation");
const approvePresentationPreparation = callable("approve_presentation_preparation");
const preparePresentationIntegration = callable("prepare_presentation_integration");
const getProcessReleaseStatus = callable("get_process_release_status");
const previewProcessRelease = callable("preview_process_release");
const approveProcessRelease = callable("approve_process_release");
const executeProcessRelease = callable("execute_process_release");
const acknowledgeProcessRelease = callable("acknowledge_process_release");

function isSteamSuspendStore(value) {
    if (typeof value !== "object" || value === null) {
        return false;
    }
    const candidate = value;
    return (typeof candidate.BlockSuspendAction === "function"
        && typeof candidate.OnSuspendRequest === "function"
        && typeof candidate.RequestSleep === "function");
}
function createSteamSuspendAdapter(resolveStore, patchBefore) {
    let store;
    try {
        const candidate = resolveStore();
        if (!isSteamSuspendStore(candidate)) {
            return null;
        }
        store = candidate;
    }
    catch {
        return null;
    }
    return {
        acquireBlocker() {
            const nativeRelease = store.BlockSuspendAction.call(store);
            if (typeof nativeRelease !== "function") {
                throw new Error("Steam returned an invalid suspend-blocker lease");
            }
            let released = false;
            return () => {
                if (released) {
                    return;
                }
                released = true;
                nativeRelease();
            };
        },
        observeSuspendRequests(handler) {
            const patch = patchBefore(store, "OnSuspendRequest", () => handler());
            let unpatched = false;
            return () => {
                if (unpatched) {
                    return;
                }
                unpatched = true;
                patch.unpatch();
            };
        },
    };
}

function createDeckySteamSuspendAdapter() {
    return createSteamSuspendAdapter(() => DFL.findModuleExport((candidate) => isSteamSuspendStore(candidate)), (object, property, handler) => DFL.beforePatch(object, property, handler));
}

function humanize(value) {
    return value.replaceAll("_", " ").replaceAll(".", " ");
}
function yesNoUnknown(value) {
    return value === true ? "yes" : value === false ? "no" : "unknown";
}
function diagnosticOverlayRows(payload, dockedIgpuStatus = null, loggingStatus = null, peripheralStatus = null) {
    if (!payload) {
        return [];
    }
    const { snapshot } = payload;
    const renderer = snapshot.gpus.find((gpu) => gpu.selected_for_render === true);
    const externalGpu = snapshot.gpus.find((gpu) => gpu.role === "external");
    const externalDisplay = snapshot.displays.find((display) => display.kind === "external");
    const disconnect = snapshot.disconnect_readiness;
    const profiles = payload.diagnostics.hardware_profiles;
    const capabilities = new Map(profiles.capabilities.map((capability) => [capability.axis, capability]));
    const capability = (axis) => {
        const value = capabilities.get(axis);
        return value ? `${humanize(value.value)} · ${humanize(value.confidence)}` : "unknown";
    };
    const rows = [
        { name: "Observed mode", value: humanize(payload.inference.mode) },
        { name: "Snapshot schema", value: String(snapshot.schema_version) },
        { name: "Device profile", value: snapshot.host_profile },
        { name: "Support tier", value: humanize(snapshot.support_tier) },
        {
            name: "Profile evidence",
            value: `host ${humanize(profiles.host.status)} · eGPU ${humanize(profiles.egpu.status)}`,
        },
        { name: "eGPU transport", value: capability("egpu_transport") },
        {
            name: "Display capability",
            value: `output ${capability("external_display_output")} · handoff ${capability("display_handoff")}`,
        },
        {
            name: "Audio capability",
            value: `output ${capability("external_audio_output")} · handoff ${capability("audio_handoff")}`,
        },
        {
            name: "Controller capability",
            value: `promote ${capability("external_controller_promotion")} · suppress ${capability("internal_controller_suppression")}`,
        },
        {
            name: "Sleep and removal",
            value: `${capability("sleep_behavior")} · ${capability("removal_behavior")}`,
        },
        {
            name: "Gamescope",
            value: `${yesNoUnknown(snapshot.gamescope.running)} · ${humanize(snapshot.gamescope.confidence)}`,
        },
        {
            name: "Observed renderer",
            value: renderer ? `${humanize(renderer.role)} · ${humanize(renderer.confidence)}` : "unknown",
        },
        {
            name: "External GPU",
            value: externalGpu
                ? `present ${yesNoUnknown(externalGpu.present)} · ${humanize(externalGpu.confidence)}`
                : "not observed",
        },
        {
            name: "External display",
            value: externalDisplay
                ? `connected ${yesNoUnknown(externalDisplay.connected)} · active ${yesNoUnknown(externalDisplay.active)} · ${humanize(externalDisplay.confidence)}`
                : "not observed",
        },
        {
            name: "Sleep flow",
            value: snapshot.sleep_guard.required
                ? snapshot.sleep_guard.active ? "guard active" : "guard required but inactive"
                : "guard not required",
        },
        {
            name: "Disconnect scan",
            value: disconnect.applicable
                ? `${disconnect.scan_complete ? "complete" : "incomplete"} · ${disconnect.ready ? "software ready" : "blocked"}`
                : "not applicable",
        },
        {
            name: "Blocker codes",
            value: snapshot.blockers.length
                ? snapshot.blockers.map((blocker) => blocker.code).join(", ")
                : "none",
        },
        {
            name: "Stage timings",
            value: payload.diagnostics.timings_ms
                .map((timing) => `${timing.stage} ${Math.round(timing.duration_ms)}ms`)
                .join(" · ") || "unavailable",
        },
        {
            name: "Verbose logging",
            value: diagnosticLoggingLabel(loggingStatus),
        },
        {
            name: "Peripheral observation",
            value: peripheralStatus
                ? `controller ${peripheralStatus.controller.exact ? "mapped" : "unmapped"} · audio ${peripheralStatus.audio.exact ? "mapped" : "unmapped"}`
                : "unavailable",
        },
        {
            name: "Peripheral evidence",
            value: peripheralStatus
                ? `${humanize(peripheralStatus.controller.code)} · ${humanize(peripheralStatus.audio.code)}`
                : "unavailable",
        },
    ];
    rows.push(...(dockedIgpuStatus
        ? [
            {
                name: "Docked-iGPU watch",
                value: `${humanize(dockedIgpuStatus.stage)} · ${humanize(dockedIgpuStatus.code)}`,
            },
            {
                name: "Promotion inspection",
                value: dockedIgpuStatus.inspection_available
                    ? "available · read-only"
                    : "unavailable",
            },
        ]
        : [
            {
                name: "Docked-iGPU watch",
                value: "unavailable",
            },
        ]));
    disconnect.clients.forEach((client, index) => {
        rows.push({
            name: `Client ${index + 1}`,
            value: `${client.name} · ${humanize(client.kind)} · ${client.resources.map(humanize).join(", ")}`,
        });
    });
    return rows;
}
function diagnosticLoggingLabel(status) {
    if (!status) {
        return "unavailable";
    }
    if (!status.enabled) {
        return `off · ${humanize(status.code)}`;
    }
    if (status.mode === "until_reboot") {
        return "on · until reboot";
    }
    const remaining = Math.max(0, status.remaining_seconds ?? 0);
    const hours = Math.floor(remaining / 3600);
    const minutes = Math.ceil((remaining % 3600) / 60);
    const countdown = hours > 0
        ? `${hours}h ${minutes}m remaining`
        : `${minutes}m remaining`;
    return `on · ${countdown}`;
}

const DISCOVERY_REFRESH_MS = 1_000;
const SETTLING_REFRESH_MS = 750;
const STABLE_REFRESH_MS = 3_000;
function firstHardwareBlocker(payload) {
    const blocker = payload.snapshot.blockers.find((item) => (item.code === "egpu_identity_unverified"
        || item.code === "drm_inventory_unavailable"
        || item.code === "active_display_unknown"
        || item.code === "render_gpu_unknown"
        || item.code === "gamescope_unverified"
        || item.code === "render_selector_conflict"
        || item.code === "game_state_unknown"));
    return blocker?.message ?? "Waiting for complete hardware evidence.";
}
function connectionProgress(payload) {
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
    const external = snapshot.displays.filter((display) => display.kind === "external" && display.connected === true);
    if (external.length === 0) {
        return {
            label: "G1 detected",
            detail: "Waiting for a connected TV output.",
            settling: false,
        };
    }
    if (external.length !== 1
        || external[0].edid_ready !== true
        || external[0].active === null) {
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
function refreshDelayForSnapshot(payload) {
    if (!payload) {
        return SETTLING_REFRESH_MS;
    }
    const { snapshot } = payload;
    const progress = connectionProgress(payload);
    if (progress.settling
        || !snapshot.disconnect_readiness.scan_complete
        || snapshot.sleep_guard.confidence === "unknown"
        || (snapshot.sleep_guard.required && !snapshot.sleep_guard.active)) {
        return SETTLING_REFRESH_MS;
    }
    return progress.label === "TV Docked" ? STABLE_REFRESH_MS : DISCOVERY_REFRESH_MS;
}

function processReleaseOutcomeMessage(outcome) {
    if (!outcome.accepted) {
        return "Process-release approval expired or was rejected. Inspect again.";
    }
    if (outcome.software_blockers_cleared) {
        return "Software blockers cleared. Physical G1 removal is still not authorized; shut down before disconnecting.";
    }
    if (outcome.force_receipt_token) {
        return "A process still holds the G1. Force close requires a separate confirmation and may lose unsaved work.";
    }
    if (outcome.action_required) {
        return "Process release needs attention. Acknowledge the result, inspect again, and do not disconnect the G1.";
    }
    return "Software blockers remain. Acknowledge the result and inspect again; do not disconnect the G1.";
}
function canOfferForce(outcome) {
    return Boolean(outcome.accepted
        && !outcome.software_blockers_cleared
        && outcome.force_receipt_token
        && outcome.acknowledgement_id);
}

function messageFrom(error) {
    return error instanceof Error && error.message
        ? error.message
        : "Unknown Steam preflight error";
}
function requiresPreflightBlocker(observation) {
    return !(observation.kind === "fresh"
        && observation.guardRequired === false
        && observation.guardConfidence === "verified");
}
function observationFromSnapshotEvidence(evidence, nowMs, staleAfterMs) {
    const observedAtMs = Date.parse(evidence.observedAt);
    const ageMs = nowMs - observedAtMs;
    if (evidence.schemaVersion !== 3
        || !Number.isFinite(observedAtMs)
        || ageMs > staleAfterMs
        || ageMs < -staleAfterMs) {
        return { kind: "stale" };
    }
    return {
        kind: "fresh",
        guardRequired: evidence.guardRequired,
        guardConfidence: evidence.guardConfidence,
        gameState: evidence.gameState,
        gameUsesEgpu: evidence.gameUsesEgpu,
    };
}
function warningForBlockedAttempt(observation) {
    if (observation.kind === "fresh"
        && observation.guardRequired
        && observation.gameUsesEgpu) {
        return {
            kind: "game",
            title: "Sleep blocked — game is using the G1",
            body: "Close the game and restore Portable before disconnecting the eGPU. The sleep request was not started.",
            critical: true,
        };
    }
    if (observation.kind === "fresh"
        && observation.guardRequired
        && observation.gameState !== "unknown") {
        return {
            kind: "standard",
            title: "Sleep blocked while G1 is attached",
            body: "This eGPU is known to wake the handheld immediately. Restore Portable and shut down before disconnecting it.",
            critical: false,
        };
    }
    return {
        kind: "unknown",
        title: "Sleep blocked — safety state is unknown",
        body: "HDM could not verify that the G1 is safely absent, so the sleep request was not started.",
        critical: true,
    };
}
class SleepPreflightCoordinator {
    adapter;
    onBlockedAttempt;
    blockerRelease = null;
    observerRelease = null;
    observation = { kind: "loading" };
    started = false;
    stopped = false;
    acquireFailed = false;
    lifecycleError = "";
    constructor(adapter, onBlockedAttempt) {
        this.adapter = adapter;
        this.onBlockedAttempt = onBlockedAttempt;
    }
    start() {
        if (this.started || this.stopped) {
            return this.status();
        }
        this.started = true;
        // The blocker must exist before any asynchronous snapshot request starts.
        this.acquireBlocker();
        if (this.adapter && this.blockerRelease) {
            try {
                this.observerRelease = this.adapter.observeSuspendRequests(() => {
                    if (this.blockerRelease) {
                        this.onBlockedAttempt(warningForBlockedAttempt(this.observation));
                    }
                });
            }
            catch (error) {
                this.lifecycleError = `Sleep is blocked, but the attempted-action warning is unavailable: ${messageFrom(error)}`;
            }
        }
        return this.status();
    }
    reconcile(observation) {
        if (this.stopped) {
            return this.status();
        }
        this.observation = observation;
        if (requiresPreflightBlocker(observation)) {
            this.acquireBlocker();
        }
        else {
            this.releaseBlocker();
        }
        return this.status();
    }
    stop() {
        if (this.stopped) {
            return this.status();
        }
        this.stopped = true;
        const releaseObserver = this.observerRelease;
        this.observerRelease = null;
        if (releaseObserver) {
            try {
                releaseObserver();
            }
            catch (error) {
                this.lifecycleError = `Failed to remove the Steam sleep warning hook: ${messageFrom(error)}`;
            }
        }
        this.releaseBlocker();
        return this.status();
    }
    status() {
        const reason = this.observation.kind === "fresh"
            ? this.observation.guardRequired
                ? "required"
                : "verified_absent"
            : this.observation.kind;
        if (!this.adapter || this.acquireFailed) {
            return {
                state: "unavailable",
                blocking: false,
                attemptWarningAvailable: false,
                reason,
                error: this.lifecycleError || "Steam's native suspend blocker could not be resolved.",
            };
        }
        if (this.blockerRelease) {
            return {
                state: "active",
                blocking: true,
                attemptWarningAvailable: this.observerRelease !== null,
                reason,
                error: this.lifecycleError,
            };
        }
        return {
            state: "inactive",
            blocking: false,
            attemptWarningAvailable: false,
            reason,
            error: this.lifecycleError,
        };
    }
    acquireBlocker() {
        if (!this.started
            || this.stopped
            || !this.adapter
            || this.blockerRelease
            || this.acquireFailed) {
            return;
        }
        try {
            const release = this.adapter.acquireBlocker();
            if (typeof release !== "function") {
                throw new Error("Steam did not return a suspend-blocker release callback");
            }
            this.blockerRelease = release;
        }
        catch (error) {
            // Do not retry in the same plugin lifecycle: a failed call may have
            // incremented Steam's blocker count without returning its release handle.
            this.acquireFailed = true;
            this.lifecycleError = `Steam preflight acquisition failed: ${messageFrom(error)}`;
        }
    }
    releaseBlocker() {
        const release = this.blockerRelease;
        this.blockerRelease = null;
        if (!release) {
            return;
        }
        try {
            release();
        }
        catch (error) {
            this.acquireFailed = true;
            this.lifecycleError = `Steam preflight release failed: ${messageFrom(error)}`;
        }
    }
}

const LABELS = {
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
];
function label(value) {
    return LABELS[value] ?? value.replaceAll("_", " ").replaceAll(".", " ");
}
function DiagnosticRow({ name, value }) {
    return (SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsxs("div", { style: { display: "flex", justifyContent: "space-between", gap: "12px", width: "100%" }, children: [SP_JSX.jsx("span", { children: name }), SP_JSX.jsx("span", { style: { opacity: 0.72, textAlign: "right" }, children: value })] }) }));
}
function showSupportBundlePreview(preview, onClose) {
    let modal;
    const close = () => {
        modal.Close();
        onClose();
    };
    // Let Decky resolve Steam's visible SP window. This plugin executes in the
    // invisible SharedJSContext, so using its global window hides the dialog.
    modal = DFL.showModal(SP_JSX.jsx(DFL.ConfirmModal, { strTitle: "Redacted support bundle preview", strOKButtonText: "Close preview", bAlertDialog: true, bDisableBackgroundDismiss: true, bHideCloseIcon: true, onOK: close, children: SP_JSX.jsxs("div", { style: { fontSize: "12px", lineHeight: "17px" }, children: [SP_JSX.jsx("p", { children: "Review this exact redacted JSON before copying or saving it. The save approval expires after five minutes and can be used once." }), SP_JSX.jsx("div", { style: { maxHeight: "55vh", overflow: "hidden" }, children: SP_JSX.jsx(DFL.ScrollPanel, { children: SP_JSX.jsx("pre", { style: { whiteSpace: "pre-wrap" }, children: preview.preview_json }) }) })] }) }), undefined, { strTitle: "Handheld Dock Mode", bNeverPopOut: true });
    return modal;
}
function showPresentationPreparationConfirmation(onConfirm, onClose) {
    let modal;
    const close = () => {
        modal.Close();
        onClose();
    };
    modal = DFL.showModal(SP_JSX.jsx(DFL.ConfirmModal, { strTitle: "Prepare experimental display validation?", strOKButtonText: "Prepare", strCancelButtonText: "Cancel", bDestructiveWarning: true, bDisableBackgroundDismiss: true, bHideCloseIcon: true, onOK: () => {
            close();
            onConfirm();
        }, onCancel: close, children: SP_JSX.jsxs("div", { style: { fontSize: "13px", lineHeight: "18px" }, children: [SP_JSX.jsx("p", { children: "Continue only with the G1 disconnected, no game running, and the Ally screen visible." }), SP_JSX.jsx("p", { children: "This installs HDM's reversible Gamescope startup integration and reloads the user service configuration. It does not restart Gamescope, switch displays, or select a GPU." })] }) }), undefined, { strTitle: "Handheld Dock Mode", bNeverPopOut: true });
    return modal;
}
function showProcessReleaseConfirmation(preview, onConfirm, onClose) {
    let modal;
    const force = preview.phase === "force";
    const close = () => {
        modal.Close();
        onClose();
    };
    modal = DFL.showModal(SP_JSX.jsx(DFL.ConfirmModal, { strTitle: force ? "Force close eGPU processes?" : "Close eGPU processes?", strOKButtonText: force ? "Force close" : "Close gracefully", strCancelButtonText: "Cancel", bDestructiveWarning: true, bDisableBackgroundDismiss: true, bHideCloseIcon: true, onOK: () => {
            close();
            onConfirm();
        }, onCancel: close, children: SP_JSX.jsxs("div", { style: { fontSize: "13px", lineHeight: "18px" }, children: [SP_JSX.jsx("p", { children: force
                        ? "Force close may lose unsaved work. Only the exact processes that survived the approved graceful attempt are eligible."
                        : "HDM will request a graceful close only for the exact ordinary user processes listed below." }), preview.targets.map((target, index) => (SP_JSX.jsxs("p", { children: [target.name, " \u2014 ", target.resources.map(label).join(", ")] }, `${target.name}-${index}`))), preview.protected_client_count > 0 && (SP_JSX.jsxs("p", { children: [preview.protected_client_count, " protected client(s) will not be closed."] })), SP_JSX.jsx("p", { children: "Clearing software clients does not authorize physical G1 removal. Shut down before disconnecting the G1." })] }) }), undefined, { strTitle: "Handheld Dock Mode", bNeverPopOut: true });
    return modal;
}
function showDiagnosticLoggingConfirmation(durationLabel, onConfirm, onClose) {
    let modal;
    const close = () => {
        modal.Close();
        onClose();
    };
    modal = DFL.showModal(SP_JSX.jsx(DFL.ConfirmModal, { strTitle: "Enable verbose HDM diagnostics?", strOKButtonText: "Enable", strCancelButtonText: "Cancel", bDisableBackgroundDismiss: true, bHideCloseIcon: true, onOK: () => {
            close();
            onConfirm();
        }, onCancel: close, children: SP_JSX.jsxs("div", { style: { fontSize: "13px", lineHeight: "18px" }, children: [SP_JSX.jsxs("p", { children: ["HDM will retain additional sanitized, HDM-only events for ", durationLabel, ". Storage remains capped and verbose logging will not survive a reboot."] }), SP_JSX.jsx("p", { children: "Logs stay on this handheld unless you separately preview, save, and share a support bundle." })] }) }), undefined, { strTitle: "Handheld Dock Mode", bNeverPopOut: true });
    return modal;
}
function MonitorIcon() {
    return (SP_JSX.jsxs("svg", { width: "24", height: "24", viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: "2", children: [SP_JSX.jsx("rect", { x: "3", y: "4", width: "18", height: "13", rx: "2" }), SP_JSX.jsx("path", { d: "M8 21h8M12 17v4" })] }));
}
function preflightObservation(payload) {
    const { snapshot } = payload;
    return observationFromSnapshotEvidence({
        schemaVersion: snapshot.schema_version,
        observedAt: snapshot.observed_at,
        guardRequired: snapshot.sleep_guard.required,
        guardConfidence: snapshot.sleep_guard.confidence,
        gameState: snapshot.game_state,
        gameUsesEgpu: snapshot.disconnect_readiness.clients.some((client) => client.kind === "game"),
    }, Date.now(), SNAPSHOT_STALE_AFTER_MS);
}
function Content({ preflight }) {
    const [payload, setPayload] = SP_REACT.useState(null);
    const [peripheralStatus, setPeripheralStatus] = SP_REACT.useState(null);
    const [dockedIgpuStatus, setDockedIgpuStatus] = SP_REACT.useState(null);
    const [dockedIgpuMessage, setDockedIgpuMessage] = SP_REACT.useState("");
    const [diagnosticLoggingStatus, setDiagnosticLoggingStatus] = SP_REACT.useState(null);
    const [diagnosticLoggingDuration, setDiagnosticLoggingDuration] = SP_REACT.useState("2_hours");
    const [diagnosticLoggingBusy, setDiagnosticLoggingBusy] = SP_REACT.useState(false);
    const [diagnosticLoggingMessage, setDiagnosticLoggingMessage] = SP_REACT.useState("");
    const [error, setError] = SP_REACT.useState("");
    const [loading, setLoading] = SP_REACT.useState(true);
    const [preflightStatus, setPreflightStatus] = SP_REACT.useState(() => preflight.status());
    const [sleepWarningHidden, setSleepWarningHidden] = SP_REACT.useState(() => localStorage.getItem(SLEEP_WARNING_KEY) === "1");
    const [supportPreview, setSupportPreview] = SP_REACT.useState(null);
    const [supportBusy, setSupportBusy] = SP_REACT.useState(false);
    const [supportMessage, setSupportMessage] = SP_REACT.useState("");
    const [showDiagnostics, setShowDiagnostics] = SP_REACT.useState(false);
    const [presentationBusy, setPresentationBusy] = SP_REACT.useState(false);
    const [presentationMessage, setPresentationMessage] = SP_REACT.useState("");
    const [processBusy, setProcessBusy] = SP_REACT.useState(false);
    const [processMessage, setProcessMessage] = SP_REACT.useState("");
    const [processAcknowledgementId, setProcessAcknowledgementId] = SP_REACT.useState("");
    const [forceReceiptToken, setForceReceiptToken] = SP_REACT.useState("");
    const lastSnapshotAt = SP_REACT.useRef(null);
    const refreshInFlight = SP_REACT.useRef(false);
    const warningToastShown = SP_REACT.useRef(false);
    const inactiveToastShown = SP_REACT.useRef(false);
    const supportModal = SP_REACT.useRef(null);
    const presentationModal = SP_REACT.useRef(null);
    const processModal = SP_REACT.useRef(null);
    const diagnosticLoggingModal = SP_REACT.useRef(null);
    SP_REACT.useEffect(() => () => {
        supportModal.current?.Close();
        supportModal.current = null;
        presentationModal.current?.Close();
        presentationModal.current = null;
        processModal.current?.Close();
        processModal.current = null;
        diagnosticLoggingModal.current?.Close();
        diagnosticLoggingModal.current = null;
    }, []);
    SP_REACT.useEffect(() => {
        let disposed = false;
        void getProcessReleaseStatus().then((status) => {
            if (disposed || status.code === "process_release.idle") {
                return;
            }
            if (status.acknowledgement_required && status.acknowledgement_id) {
                setProcessAcknowledgementId(status.acknowledgement_id);
            }
            setProcessMessage(status.action_required
                ? "A prior process-release attempt needs acknowledgement. Do not disconnect the G1."
                : `Previous process-release result: ${label(status.code)}.`);
        }).catch(() => {
            if (!disposed) {
                setProcessMessage("Process-release safety state is unavailable. Do not disconnect the G1.");
            }
        });
        return () => {
            disposed = true;
        };
    }, []);
    const refresh = SP_REACT.useCallback(async (quiet = false) => {
        if (refreshInFlight.current) {
            return null;
        }
        refreshInFlight.current = true;
        if (!quiet) {
            setLoading(true);
            setError("");
        }
        try {
            const [nextPayload, nextDockedIgpuStatus, nextDiagnosticLoggingStatus, nextPeripheralStatus] = await Promise.all([
                getSnapshot(),
                getDockedIgpuStatus().catch(() => null),
                getDiagnosticLoggingStatus().catch(() => null),
                getPeripheralStatus().catch(() => null),
            ]);
            setPayload(nextPayload);
            setDockedIgpuStatus(nextDockedIgpuStatus);
            setDiagnosticLoggingStatus(nextDiagnosticLoggingStatus);
            setPeripheralStatus(nextPeripheralStatus);
            setError("");
            lastSnapshotAt.current = Date.now();
            setPreflightStatus(preflight.reconcile(preflightObservation(nextPayload)));
            return nextPayload;
        }
        catch {
            setError("Read-only snapshot unavailable. Check the Decky log for details.");
            setPreflightStatus(preflight.reconcile({ kind: "unavailable" }));
            return null;
        }
        finally {
            refreshInFlight.current = false;
            if (!quiet) {
                setLoading(false);
            }
        }
    }, [preflight]);
    SP_REACT.useEffect(() => {
        let disposed = false;
        let timer = null;
        const poll = async (quiet) => {
            if (lastSnapshotAt.current !== null
                && Date.now() - lastSnapshotAt.current > SNAPSHOT_STALE_AFTER_MS) {
                setPreflightStatus(preflight.reconcile({ kind: "stale" }));
            }
            const nextPayload = await refresh(quiet);
            if (!disposed) {
                timer = window.setTimeout(() => void poll(true), refreshDelayForSnapshot(nextPayload));
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
    const totalTiming = payload?.diagnostics.timings_ms.find((timing) => timing.stage === "snapshot_total");
    const gameUsesEgpu = disconnect?.clients.some((client) => client.kind === "game") ?? false;
    const closeEligibleClientCount = disconnect?.clients.filter((client) => client.kind === "user" && client.close_eligible).length ?? 0;
    const disconnectStatus = loading
        ? "Reading…"
        : !disconnect?.applicable
            ? "eGPU not connected"
            : !disconnect.scan_complete
                ? "Scan incomplete — blocked"
                : disconnect.ready
                    ? "Ready"
                    : "Blocked";
    const overlayRows = diagnosticOverlayRows(payload, dockedIgpuStatus, diagnosticLoggingStatus, peripheralStatus);
    const acknowledgeDockedIgpuWatch = SP_REACT.useCallback(async () => {
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
        }
        catch {
            setDockedIgpuMessage("Watcher acknowledgement is unavailable.");
        }
    }, []);
    const applyDiagnosticLogging = SP_REACT.useCallback(async () => {
        setDiagnosticLoggingBusy(true);
        setDiagnosticLoggingMessage("");
        try {
            const status = await enableDiagnosticLogging(diagnosticLoggingDuration, true);
            setDiagnosticLoggingStatus(status);
            setDiagnosticLoggingMessage(status.enabled
                ? "Verbose diagnostics enabled. They remain local until separately exported."
                : "Verbose diagnostics were not enabled.");
        }
        catch {
            setDiagnosticLoggingMessage("Verbose diagnostics could not be enabled.");
        }
        finally {
            setDiagnosticLoggingBusy(false);
        }
    }, [diagnosticLoggingDuration]);
    const requestDiagnosticLogging = SP_REACT.useCallback(() => {
        const option = DIAGNOSTIC_LOGGING_OPTIONS.find((value) => value.data === diagnosticLoggingDuration);
        diagnosticLoggingModal.current?.Close();
        diagnosticLoggingModal.current = showDiagnosticLoggingConfirmation(option?.label ?? "the selected duration", () => void applyDiagnosticLogging(), () => {
            diagnosticLoggingModal.current = null;
        });
    }, [applyDiagnosticLogging, diagnosticLoggingDuration]);
    const stopDiagnosticLogging = SP_REACT.useCallback(async () => {
        setDiagnosticLoggingBusy(true);
        setDiagnosticLoggingMessage("");
        try {
            const status = await disableDiagnosticLogging();
            setDiagnosticLoggingStatus(status);
            setDiagnosticLoggingMessage("Verbose diagnostics disabled.");
        }
        catch {
            setDiagnosticLoggingMessage("Verbose diagnostics status is unavailable.");
        }
        finally {
            setDiagnosticLoggingBusy(false);
        }
    }, []);
    SP_REACT.useEffect(() => {
        if (!sleepGuard?.required) {
            warningToastShown.current = false;
            inactiveToastShown.current = false;
            return;
        }
        if (sleepGuard.active) {
            inactiveToastShown.current = false;
        }
        else if (!inactiveToastShown.current) {
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
    const hideSleepWarning = SP_REACT.useCallback(() => {
        localStorage.setItem(SLEEP_WARNING_KEY, "1");
        setSleepWarningHidden(true);
    }, []);
    const showSleepWarning = SP_REACT.useCallback(() => {
        localStorage.removeItem(SLEEP_WARNING_KEY);
        warningToastShown.current = false;
        setSleepWarningHidden(false);
    }, []);
    const createSupportPreview = SP_REACT.useCallback(async () => {
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
        }
        catch {
            setSupportMessage("Support bundle preview failed. No file was written.");
        }
        finally {
            setSupportBusy(false);
        }
    }, []);
    const reviewSupportPreview = SP_REACT.useCallback(() => {
        if (!supportPreview) {
            return;
        }
        supportModal.current?.Close();
        supportModal.current = showSupportBundlePreview(supportPreview, () => {
            supportModal.current = null;
        });
    }, [supportPreview]);
    const copySupportPreview = SP_REACT.useCallback(async () => {
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
        }
        catch {
            setSupportMessage("Clipboard copy is unavailable. The preview was not changed.");
        }
        finally {
            setSupportBusy(false);
        }
    }, [supportPreview]);
    const saveApprovedSupportPreview = SP_REACT.useCallback(async () => {
        if (!supportPreview) {
            return;
        }
        setSupportBusy(true);
        try {
            const result = await saveSupportBundle(supportPreview.preview_token);
            setSupportMessage(result.ok
                ? `Saved the reviewed bundle to ${result.relative_path}.`
                : "Support bundle save did not complete.");
            if (result.ok) {
                setSupportPreview(null);
            }
        }
        catch {
            setSupportMessage("Save approval expired or failed. Create and review a new preview.");
            setSupportPreview(null);
        }
        finally {
            setSupportBusy(false);
        }
    }, [supportPreview]);
    const preparePresentation = SP_REACT.useCallback(async () => {
        setPresentationBusy(true);
        setPresentationMessage("");
        try {
            const approval = await approvePresentationPreparation();
            if (!approval.approval_token || approval.blockers.length > 0) {
                setPresentationMessage(approval.blockers.length > 0
                    ? `Preparation blocked: ${approval.blockers.map(label).join(", ")}.`
                    : "Preparation approval was not issued. Inspect again.");
                return;
            }
            const outcome = await preparePresentationIntegration(approval.approval_token);
            setPresentationMessage(outcome.prepared
                ? outcome.changed
                    ? "Gamescope validation integration prepared. Gamescope was not restarted."
                    : "Gamescope validation integration was already prepared."
                : outcome.rollback_attempted && !outcome.rollback_succeeded
                    ? "Preparation failed and rollback needs attention. Do not restart Gamescope."
                    : `Preparation did not complete: ${label(outcome.code)}.`);
        }
        catch {
            setPresentationMessage("Preparation failed safely. Gamescope was not intentionally restarted.");
        }
        finally {
            setPresentationBusy(false);
        }
    }, []);
    const inspectPresentationPreparation = SP_REACT.useCallback(async () => {
        setPresentationBusy(true);
        setPresentationMessage("");
        try {
            const preview = await previewPresentationPreparation();
            if (preview.blockers.length > 0) {
                setPresentationMessage(`Preparation blocked: ${preview.blockers.map(label).join(", ")}.`);
                return;
            }
            if (preview.ready) {
                setPresentationMessage("Gamescope validation integration is already prepared.");
                return;
            }
            presentationModal.current?.Close();
            presentationModal.current = showPresentationPreparationConfirmation(() => void preparePresentation(), () => {
                presentationModal.current = null;
            });
        }
        catch {
            setPresentationMessage("Preparation inspection is unavailable. No change was made.");
        }
        finally {
            setPresentationBusy(false);
        }
    }, [preparePresentation]);
    const runProcessRelease = SP_REACT.useCallback(async (phase, receiptToken) => {
        setProcessBusy(true);
        setProcessMessage("");
        try {
            const approval = await approveProcessRelease(phase, receiptToken);
            if (!approval.approval_token || approval.blockers.length > 0) {
                setProcessMessage(approval.blockers.length > 0
                    ? `Process release blocked: ${approval.blockers.map(label).join(", ")}.`
                    : "Process-release approval was not issued. Inspect again.");
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
        }
        catch {
            setProcessMessage("Process release failed closed. Do not disconnect the G1.");
            if (phase === "force") {
                setForceReceiptToken("");
            }
        }
        finally {
            setProcessBusy(false);
        }
    }, [refresh]);
    const inspectProcessRelease = SP_REACT.useCallback(async (phase, receiptToken = "") => {
        setProcessBusy(true);
        setProcessMessage("");
        try {
            const preview = await previewProcessRelease(phase, receiptToken);
            if (!preview.ready || preview.blockers.length > 0 || preview.targets.length === 0) {
                setProcessMessage(preview.blockers.length > 0
                    ? `Process release blocked: ${preview.blockers.map(label).join(", ")}.`
                    : "No eligible ordinary user process is holding the G1.");
                return;
            }
            processModal.current?.Close();
            processModal.current = showProcessReleaseConfirmation(preview, () => void runProcessRelease(phase, receiptToken), () => {
                processModal.current = null;
            });
        }
        catch {
            setProcessMessage("Process-release inspection is unavailable. No process was signaled.");
        }
        finally {
            setProcessBusy(false);
        }
    }, [runProcessRelease]);
    const acknowledgeProcessResult = SP_REACT.useCallback(async () => {
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
        }
        catch {
            setProcessMessage("Process-release acknowledgement failed.");
        }
        finally {
            setProcessBusy(false);
        }
    }, [processAcknowledgementId]);
    const reviewForceClose = SP_REACT.useCallback(async () => {
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
        }
        catch {
            setProcessMessage("Force-close review is unavailable. No process was signaled.");
        }
        finally {
            setProcessBusy(false);
        }
    }, [forceReceiptToken, inspectProcessRelease, processAcknowledgementId]);
    return (SP_JSX.jsxs(SP_JSX.Fragment, { children: [SP_JSX.jsxs(DFL.PanelSection, { title: "Observed state", children: [SP_JSX.jsx(DiagnosticRow, { name: "Connection", value: progress.label }), SP_JSX.jsx(DiagnosticRow, { name: "Mode", value: loading ? "Reading…" : label(payload?.inference.mode ?? "unknown") }), SP_JSX.jsx(DiagnosticRow, { name: "Game", value: label(snapshot?.game_state ?? "unknown") }), SP_JSX.jsx(DiagnosticRow, { name: "Render GPU", value: renderer ? label(renderer.role) : "Unknown" }), SP_JSX.jsx(DiagnosticRow, { name: "Active display", value: display ? label(display.kind) : "Unknown" }), SP_JSX.jsx(DiagnosticRow, { name: "Hardware", value: label(snapshot?.support_tier ?? "unknown") }), SP_JSX.jsx(DiagnosticRow, { name: "Snapshot time", value: totalTiming ? `${Math.round(totalTiming.duration_ms)} ms` : "Unknown" }), SP_JSX.jsx(DFL.PanelSectionRow, { children: progress.detail })] }), SP_JSX.jsxs(DFL.PanelSection, { title: "Sleep protection", children: [SP_JSX.jsx(DiagnosticRow, { name: "System inhibitor", value: loading
                            ? "Checking…"
                            : sleepGuard?.required
                                ? sleepGuard.active
                                    ? "Active"
                                    : "Inactive"
                                : "Not required" }), SP_JSX.jsx(DiagnosticRow, { name: "Steam preflight", value: preflightStatus.state === "active"
                            ? preflightStatus.attemptWarningAvailable
                                ? "Active"
                                : "Blocked; warning unavailable"
                            : preflightStatus.state === "inactive"
                                ? "Standby — G1 verified absent"
                                : "Unavailable" }), preflightStatus.error && (SP_JSX.jsx(DFL.PanelSectionRow, { children: preflightStatus.error })), sleepGuard?.required && (SP_JSX.jsxs(SP_JSX.Fragment, { children: [!sleepWarningHidden && (SP_JSX.jsxs(SP_JSX.Fragment, { children: [SP_JSX.jsx(DFL.PanelSectionRow, { children: gameUsesEgpu
                                            ? "A game is using the G1. Sleep is blocked to prevent the known immediate-wake behavior and workload risk."
                                            : "The attached G1 is known to wake this handheld immediately after sleep. Sleep remains blocked until the G1 is verified absent." }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: hideSleepWarning, children: "Never show this explanation again" }) })] })), sleepWarningHidden && (SP_JSX.jsx(DFL.PanelSectionRow, { children: "The explanation is hidden. Sleep protection remains active." }))] }))] }), SP_JSX.jsxs(DFL.PanelSection, { title: "Disconnect readiness", children: [SP_JSX.jsx(DiagnosticRow, { name: "Status", value: disconnectStatus }), disconnect?.applicable && (SP_JSX.jsx(DiagnosticRow, { name: "Resource clients", value: String(disconnect.clients.length) })), (disconnect?.storage_devices ?? 0) > 0 && (SP_JSX.jsx(DiagnosticRow, { name: "eGPU storage", value: disconnect?.storage_in_use ? "In use — blocked" : "Not mounted" })), disconnect?.error && SP_JSX.jsx(DFL.PanelSectionRow, { children: disconnect.error }), closeEligibleClientCount > 0 && !processAcknowledgementId && (SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: () => void inspectProcessRelease("graceful"), disabled: processBusy, children: processBusy ? "Checking…" : "Close eligible eGPU processes" }) })), forceReceiptToken && (SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: () => void reviewForceClose(), disabled: processBusy, children: "Review force close" }) })), processAcknowledgementId && !forceReceiptToken && (SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: () => void acknowledgeProcessResult(), disabled: processBusy, children: "Acknowledge process-release result" }) })), processMessage && SP_JSX.jsx(DFL.PanelSectionRow, { children: processMessage }), SP_JSX.jsx(DFL.PanelSectionRow, { children: "Process closure always requires confirmation. Software readiness never authorizes physical G1 removal." })] }), (error || (snapshot?.blockers.length ?? 0) > 0) && (SP_JSX.jsxs(DFL.PanelSection, { title: "Needs attention", children: [error && SP_JSX.jsx(DFL.PanelSectionRow, { children: error }), snapshot?.blockers.map((blocker) => (SP_JSX.jsx(DFL.PanelSectionRow, { children: blocker.message }, blocker.code)))] })), SP_JSX.jsxs(DFL.PanelSection, { title: "Support bundle", children: [SP_JSX.jsx(DFL.PanelSectionRow, { children: "Preview a bounded HDM-only report before copying or saving it. Raw hardware IDs, addresses, usernames, home paths, and command lines are excluded or redacted." }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: () => void createSupportPreview(), disabled: supportBusy, children: supportBusy ? "Working…" : "Preview redacted support bundle" }) }), supportPreview && (SP_JSX.jsxs(SP_JSX.Fragment, { children: [SP_JSX.jsx(DiagnosticRow, { name: "Preview size", value: `${supportPreview.size_bytes} bytes` }), SP_JSX.jsx(DiagnosticRow, { name: "Recent events", value: String(supportPreview.event_count) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: reviewSupportPreview, disabled: supportBusy, children: "Review exact redacted JSON" }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: () => void copySupportPreview(), disabled: supportBusy, children: "Copy reviewed JSON" }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: () => void saveApprovedSupportPreview(), disabled: supportBusy, children: "Save reviewed bundle to Downloads" }) })] })), supportMessage && SP_JSX.jsx(DFL.PanelSectionRow, { children: supportMessage })] }), SP_JSX.jsxs(DFL.PanelSection, { title: "Diagnostics only", children: [SP_JSX.jsx(DFL.PanelSectionRow, { children: "HDM 0.2 observes state and blocks sleep while the G1 is attached. It cannot switch displays, GPUs, or Gamescope. It can close only exact eligible eGPU processes after explicit approval." }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: () => void refresh(), disabled: loading, children: loading ? "Reading…" : "Refresh" }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: () => setShowDiagnostics((value) => !value), children: showDiagnostics ? "Hide troubleshooting details" : "Show troubleshooting details" }) }), sleepGuard?.required && sleepWarningHidden && (SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: showSleepWarning, children: "Show sleep warning again" }) }))] }), showDiagnostics && (SP_JSX.jsxs(DFL.PanelSection, { title: "Troubleshooting details", children: [SP_JSX.jsx(DFL.PanelSectionRow, { children: "Read-only technical evidence. Raw hardware identities, connector names, and process IDs are hidden." }), overlayRows.map((row) => (SP_JSX.jsx(DiagnosticRow, { name: row.name, value: row.value }, row.name))), dockedIgpuStatus?.acknowledgement_required && (SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: () => void acknowledgeDockedIgpuWatch(), children: "Acknowledge Docked-iGPU watcher state" }) })), dockedIgpuMessage && (SP_JSX.jsx(DFL.PanelSectionRow, { children: dockedIgpuMessage })), SP_JSX.jsx(DFL.DropdownItem, { label: "Verbose logging duration", description: "Temporary, sanitized, capped, and off by default", rgOptions: DIAGNOSTIC_LOGGING_OPTIONS, selectedOption: diagnosticLoggingDuration, disabled: diagnosticLoggingBusy || diagnosticLoggingStatus?.enabled === true, onChange: (option) => {
                            setDiagnosticLoggingDuration(option.data);
                        } }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: diagnosticLoggingStatus?.enabled
                                ? () => void stopDiagnosticLogging()
                                : requestDiagnosticLogging, disabled: diagnosticLoggingBusy, children: diagnosticLoggingStatus?.enabled
                                ? "Disable verbose diagnostics"
                                : "Enable verbose diagnostics" }) }), diagnosticLoggingMessage && (SP_JSX.jsx(DFL.PanelSectionRow, { children: diagnosticLoggingMessage })), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: () => void inspectPresentationPreparation(), disabled: presentationBusy, children: presentationBusy ? "Checking…" : "Prepare supervised display validation" }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: "Preparation only. This control cannot restart Gamescope or switch displays." }), presentationMessage && SP_JSX.jsx(DFL.PanelSectionRow, { children: presentationMessage })] }))] }));
}
function showBlockedAttempt(warning, onClose) {
    let modal;
    const close = () => {
        modal.Close();
        onClose();
    };
    // Let Decky resolve Steam's visible SP window after the Power menu closes.
    // SharedJSContext's global window is not a player-visible modal parent.
    modal = DFL.showModal(SP_JSX.jsx(DFL.ConfirmModal, { strTitle: warning.title, strDescription: warning.body, strOKButtonText: "OK", bAlertDialog: true, bDestructiveWarning: warning.critical, bDisableBackgroundDismiss: true, bHideCloseIcon: true, onOK: close }), undefined, { strTitle: "Handheld Dock Mode", bNeverPopOut: true });
    return modal;
}
var index = definePlugin(() => {
    let warningModal = null;
    let warningTimer = null;
    const preflight = new SleepPreflightCoordinator(createDeckySteamSuspendAdapter(), (warning) => {
        if (warningTimer !== null) {
            window.clearTimeout(warningTimer);
        }
        warningModal?.Close();
        warningModal = null;
        // Steam closes the Power menu after dispatching OnSuspendRequest. Defer the
        // acknowledgement dialog so it is not discarded with that transient menu.
        warningTimer = window.setTimeout(() => {
            warningTimer = null;
            warningModal = showBlockedAttempt(warning, () => {
                warningModal = null;
            });
        }, BLOCKED_ATTEMPT_MODAL_DELAY_MS);
    });
    preflight.start();
    return {
        name: "Handheld Dock Mode",
        titleView: SP_JSX.jsx("div", { className: DFL.staticClasses.Title, children: "Handheld Dock Mode" }),
        content: SP_JSX.jsx(Content, { preflight: preflight }),
        icon: SP_JSX.jsx(MonitorIcon, {}),
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

export { index as default };
//# sourceMappingURL=index.js.map
