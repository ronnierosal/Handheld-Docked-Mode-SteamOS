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
    idle: "No game running",
    portable: "Portable",
    running: "Game running",
    tv_docked: "TV Docked",
    unknown: "Unknown",
    unsupported: "Unsupported",
};
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
    const refresh = SP_REACT.useCallback(async () => {
        setLoading(true);
        setError("");
        try {
            setPayload(await getSnapshot());
        }
        catch {
            setPayload(null);
            setError("Read-only snapshot unavailable. Check the Decky log for details.");
        }
        finally {
            setLoading(false);
        }
    }, []);
    SP_REACT.useEffect(() => {
        void refresh();
    }, [refresh]);
    const snapshot = payload?.snapshot;
    const renderer = snapshot?.gpus.find((gpu) => gpu.selected_for_render === true);
    const display = snapshot?.displays.find((item) => item.active === true);
    return (SP_JSX.jsxs(SP_JSX.Fragment, { children: [SP_JSX.jsxs(DFL.PanelSection, { title: "Observed state", children: [SP_JSX.jsx(DiagnosticRow, { name: "Mode", value: loading ? "Reading…" : label(payload?.inference.mode ?? "unknown") }), SP_JSX.jsx(DiagnosticRow, { name: "Game", value: label(snapshot?.game_state ?? "unknown") }), SP_JSX.jsx(DiagnosticRow, { name: "Render GPU", value: renderer ? label(renderer.role) : "Unknown" }), SP_JSX.jsx(DiagnosticRow, { name: "Active display", value: display ? label(display.kind) : "Unknown" }), SP_JSX.jsx(DiagnosticRow, { name: "Hardware", value: label(snapshot?.support_tier ?? "unknown") })] }), (error || (snapshot?.blockers.length ?? 0) > 0) && (SP_JSX.jsxs(DFL.PanelSection, { title: "Needs attention", children: [error && SP_JSX.jsx(DFL.PanelSectionRow, { children: error }), snapshot?.blockers.map((blocker) => (SP_JSX.jsx(DFL.PanelSectionRow, { children: blocker.message }, blocker.code)))] })), SP_JSX.jsxs(DFL.PanelSection, { title: "Diagnostics only", children: [SP_JSX.jsx(DFL.PanelSectionRow, { children: "HDM 0.1 observes the current state. It cannot switch displays, GPUs, or Gamescope." }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: () => void refresh(), disabled: loading, children: loading ? "Reading…" : "Refresh" }) })] })] }));
}
var index = definePlugin(() => ({
    name: "Handheld Dock Mode",
    titleView: SP_JSX.jsx("div", { className: DFL.staticClasses.Title, children: "Handheld Dock Mode" }),
    content: SP_JSX.jsx(Content, {}),
    icon: SP_JSX.jsx(MonitorIcon, {}),
    onDismount() { },
}));

export { index as default };
//# sourceMappingURL=index.js.map
