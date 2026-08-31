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
const previewSupportBundle = callable("preview_support_bundle");
const saveSupportBundle = callable("save_support_bundle");

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
function label(value) {
    return LABELS[value] ?? value.replaceAll("_", " ");
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
    const [error, setError] = SP_REACT.useState("");
    const [loading, setLoading] = SP_REACT.useState(true);
    const [preflightStatus, setPreflightStatus] = SP_REACT.useState(() => preflight.status());
    const [sleepWarningHidden, setSleepWarningHidden] = SP_REACT.useState(() => localStorage.getItem(SLEEP_WARNING_KEY) === "1");
    const [supportPreview, setSupportPreview] = SP_REACT.useState(null);
    const [supportBusy, setSupportBusy] = SP_REACT.useState(false);
    const [supportMessage, setSupportMessage] = SP_REACT.useState("");
    const lastSnapshotAt = SP_REACT.useRef(null);
    const refreshInFlight = SP_REACT.useRef(false);
    const warningToastShown = SP_REACT.useRef(false);
    const inactiveToastShown = SP_REACT.useRef(false);
    const supportModal = SP_REACT.useRef(null);
    SP_REACT.useEffect(() => () => {
        supportModal.current?.Close();
        supportModal.current = null;
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
            const nextPayload = await getSnapshot();
            setPayload(nextPayload);
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
    const disconnectStatus = loading
        ? "Reading…"
        : !disconnect?.applicable
            ? "eGPU not connected"
            : !disconnect.scan_complete
                ? "Scan incomplete — blocked"
                : disconnect.ready
                    ? "Ready"
                    : "Blocked";
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
                                            : "The attached G1 is known to wake this handheld immediately after sleep. Sleep remains blocked until the G1 is verified absent." }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: hideSleepWarning, children: "Never show this explanation again" }) })] })), sleepWarningHidden && (SP_JSX.jsx(DFL.PanelSectionRow, { children: "The explanation is hidden. Sleep protection remains active." }))] }))] }), SP_JSX.jsxs(DFL.PanelSection, { title: "Disconnect readiness", children: [SP_JSX.jsx(DiagnosticRow, { name: "Status", value: disconnectStatus }), disconnect?.applicable && (SP_JSX.jsx(DiagnosticRow, { name: "Resource clients", value: String(disconnect.clients.length) })), disconnect?.clients.map((client) => (SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsxs("div", { children: [SP_JSX.jsxs("div", { children: [client.name, " \u00B7 PID ", client.pid, " \u00B7 ", label(client.kind)] }), SP_JSX.jsxs("div", { style: { fontSize: "0.85em", opacity: 0.7 }, children: [client.resources.map(label).join(", "), " \u00B7 ", client.reason] })] }) }, client.instance_id))), (disconnect?.storage_devices ?? 0) > 0 && (SP_JSX.jsx(DiagnosticRow, { name: "eGPU storage", value: disconnect?.storage_in_use ? "In use — blocked" : "Not mounted" })), disconnect?.error && SP_JSX.jsx(DFL.PanelSectionRow, { children: disconnect.error }), SP_JSX.jsx(DFL.PanelSectionRow, { children: "Read-only evidence. HDM did not close processes or disconnect hardware." })] }), (error || (snapshot?.blockers.length ?? 0) > 0) && (SP_JSX.jsxs(DFL.PanelSection, { title: "Needs attention", children: [error && SP_JSX.jsx(DFL.PanelSectionRow, { children: error }), snapshot?.blockers.map((blocker) => (SP_JSX.jsx(DFL.PanelSectionRow, { children: blocker.message }, blocker.code)))] })), SP_JSX.jsxs(DFL.PanelSection, { title: "Support bundle", children: [SP_JSX.jsx(DFL.PanelSectionRow, { children: "Preview a bounded HDM-only report before copying or saving it. Raw hardware IDs, addresses, usernames, home paths, and command lines are excluded or redacted." }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: () => void createSupportPreview(), disabled: supportBusy, children: supportBusy ? "Working…" : "Preview redacted support bundle" }) }), supportPreview && (SP_JSX.jsxs(SP_JSX.Fragment, { children: [SP_JSX.jsx(DiagnosticRow, { name: "Preview size", value: `${supportPreview.size_bytes} bytes` }), SP_JSX.jsx(DiagnosticRow, { name: "Recent events", value: String(supportPreview.event_count) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: reviewSupportPreview, disabled: supportBusy, children: "Review exact redacted JSON" }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: () => void copySupportPreview(), disabled: supportBusy, children: "Copy reviewed JSON" }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: () => void saveApprovedSupportPreview(), disabled: supportBusy, children: "Save reviewed bundle to Downloads" }) })] })), supportMessage && SP_JSX.jsx(DFL.PanelSectionRow, { children: supportMessage })] }), SP_JSX.jsxs(DFL.PanelSection, { title: "Diagnostics only", children: [SP_JSX.jsx(DFL.PanelSectionRow, { children: "HDM 0.2 observes the current state and blocks sleep while the G1 is attached. It cannot switch displays, GPUs, Gamescope, or close processes." }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: () => void refresh(), disabled: loading, children: loading ? "Reading…" : "Refresh" }) }), sleepGuard?.required && sleepWarningHidden && (SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: showSleepWarning, children: "Show sleep warning again" }) }))] })] }));
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
