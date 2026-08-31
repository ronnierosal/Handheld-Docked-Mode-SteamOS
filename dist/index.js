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
function label(value) {
    return LABELS[value] ?? value.replaceAll("_", " ");
}
function DiagnosticRow({ name, value }) {
    return (SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsxs("div", { style: { display: "flex", justifyContent: "space-between", gap: "12px", width: "100%" }, children: [SP_JSX.jsx("span", { children: name }), SP_JSX.jsx("span", { style: { opacity: 0.72, textAlign: "right" }, children: value })] }) }));
}
function MonitorIcon() {
    return (SP_JSX.jsxs("svg", { width: "24", height: "24", viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: "2", children: [SP_JSX.jsx("rect", { x: "3", y: "4", width: "18", height: "13", rx: "2" }), SP_JSX.jsx("path", { d: "M8 21h8M12 17v4" })] }));
}
function Content() {
    const [payload, setPayload] = SP_REACT.useState(null);
    const [error, setError] = SP_REACT.useState("");
    const [loading, setLoading] = SP_REACT.useState(true);
    const [sleepWarningHidden, setSleepWarningHidden] = SP_REACT.useState(() => localStorage.getItem(SLEEP_WARNING_KEY) === "1");
    const warningToastShown = SP_REACT.useRef(false);
    const inactiveToastShown = SP_REACT.useRef(false);
    const refresh = SP_REACT.useCallback(async (quiet = false) => {
        if (!quiet) {
            setLoading(true);
            setError("");
        }
        try {
            setPayload(await getSnapshot());
        }
        catch {
            setError("Read-only snapshot unavailable. Check the Decky log for details.");
        }
        finally {
            if (!quiet) {
                setLoading(false);
            }
        }
    }, []);
    SP_REACT.useEffect(() => {
        void refresh();
        const timer = window.setInterval(() => void refresh(true), 3000);
        return () => window.clearInterval(timer);
    }, [refresh]);
    const snapshot = payload?.snapshot;
    const renderer = snapshot?.gpus.find((gpu) => gpu.selected_for_render === true);
    const display = snapshot?.displays.find((item) => item.active === true);
    const disconnect = snapshot?.disconnect_readiness;
    const sleepGuard = snapshot?.sleep_guard;
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
    return (SP_JSX.jsxs(SP_JSX.Fragment, { children: [SP_JSX.jsxs(DFL.PanelSection, { title: "Observed state", children: [SP_JSX.jsx(DiagnosticRow, { name: "Mode", value: loading ? "Reading…" : label(payload?.inference.mode ?? "unknown") }), SP_JSX.jsx(DiagnosticRow, { name: "Game", value: label(snapshot?.game_state ?? "unknown") }), SP_JSX.jsx(DiagnosticRow, { name: "Render GPU", value: renderer ? label(renderer.role) : "Unknown" }), SP_JSX.jsx(DiagnosticRow, { name: "Active display", value: display ? label(display.kind) : "Unknown" }), SP_JSX.jsx(DiagnosticRow, { name: "Hardware", value: label(snapshot?.support_tier ?? "unknown") })] }), sleepGuard?.required && (SP_JSX.jsxs(DFL.PanelSection, { title: "Sleep protection", children: [SP_JSX.jsx(DiagnosticRow, { name: "Sleep", value: sleepGuard.active ? "Blocked while G1 attached" : "Protection inactive" }), !sleepWarningHidden && (SP_JSX.jsxs(SP_JSX.Fragment, { children: [SP_JSX.jsx(DFL.PanelSectionRow, { children: gameUsesEgpu
                                    ? "A game is using the G1. Sleep is blocked to prevent the known immediate-wake behavior and workload risk."
                                    : "The attached G1 is known to wake this handheld immediately after sleep. Sleep remains blocked until the G1 is verified absent." }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: hideSleepWarning, children: "Never show this explanation again" }) })] })), sleepWarningHidden && (SP_JSX.jsx(DFL.PanelSectionRow, { children: "The explanation is hidden. Sleep protection remains active." }))] })), SP_JSX.jsxs(DFL.PanelSection, { title: "Disconnect readiness", children: [SP_JSX.jsx(DiagnosticRow, { name: "Status", value: disconnectStatus }), disconnect?.applicable && (SP_JSX.jsx(DiagnosticRow, { name: "Resource clients", value: String(disconnect.clients.length) })), disconnect?.clients.map((client) => (SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsxs("div", { children: [SP_JSX.jsxs("div", { children: [client.name, " \u00B7 PID ", client.pid, " \u00B7 ", label(client.kind)] }), SP_JSX.jsxs("div", { style: { fontSize: "0.85em", opacity: 0.7 }, children: [client.resources.map(label).join(", "), " \u00B7 ", client.reason] })] }) }, client.instance_id))), (disconnect?.storage_devices ?? 0) > 0 && (SP_JSX.jsx(DiagnosticRow, { name: "eGPU storage", value: disconnect?.storage_in_use ? "In use — blocked" : "Not mounted" })), disconnect?.error && SP_JSX.jsx(DFL.PanelSectionRow, { children: disconnect.error }), SP_JSX.jsx(DFL.PanelSectionRow, { children: "Read-only evidence. HDM did not close processes or disconnect hardware." })] }), (error || (snapshot?.blockers.length ?? 0) > 0) && (SP_JSX.jsxs(DFL.PanelSection, { title: "Needs attention", children: [error && SP_JSX.jsx(DFL.PanelSectionRow, { children: error }), snapshot?.blockers.map((blocker) => (SP_JSX.jsx(DFL.PanelSectionRow, { children: blocker.message }, blocker.code)))] })), SP_JSX.jsxs(DFL.PanelSection, { title: "Diagnostics only", children: [SP_JSX.jsx(DFL.PanelSectionRow, { children: "HDM 0.2 observes the current state and blocks sleep while the G1 is attached. It cannot switch displays, GPUs, Gamescope, or close processes." }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: () => void refresh(), disabled: loading, children: loading ? "Reading…" : "Refresh" }) }), sleepGuard?.required && sleepWarningHidden && (SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: showSleepWarning, children: "Show sleep warning again" }) }))] })] }));
}
var index = definePlugin(() => ({
    name: "Handheld Dock Mode",
    titleView: SP_JSX.jsx("div", { className: DFL.staticClasses.Title, children: "Handheld Dock Mode" }),
    content: SP_JSX.jsx(Content, {}),
    icon: SP_JSX.jsx(MonitorIcon, {}),
    alwaysRender: true,
    onDismount() { },
}));

export { index as default };
//# sourceMappingURL=index.js.map
