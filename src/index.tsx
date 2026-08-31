import { definePlugin } from "@decky/api";
import {
  ButtonItem,
  PanelSection,
  PanelSectionRow,
  staticClasses,
} from "@decky/ui";
import { useCallback, useEffect, useState } from "react";

import { getSnapshot, type SnapshotPayload } from "./backend";


const LABELS: Record<string, string> = {
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

function label(value: string): string {
  return LABELS[value] ?? value.replaceAll("_", " ");
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

function Content() {
  const [payload, setPayload] = useState<SnapshotPayload | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setPayload(await getSnapshot());
    } catch {
      setPayload(null);
      setError("Read-only snapshot unavailable. Check the Decky log for details.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const snapshot = payload?.snapshot;
  const renderer = snapshot?.gpus.find((gpu) => gpu.selected_for_render === true);
  const display = snapshot?.displays.find((item) => item.active === true);

  return (
    <>
      <PanelSection title="Observed state">
        <DiagnosticRow name="Mode" value={loading ? "Reading…" : label(payload?.inference.mode ?? "unknown")} />
        <DiagnosticRow name="Game" value={label(snapshot?.game_state ?? "unknown")} />
        <DiagnosticRow name="Render GPU" value={renderer ? label(renderer.role) : "Unknown"} />
        <DiagnosticRow name="Active display" value={display ? label(display.kind) : "Unknown"} />
        <DiagnosticRow name="Hardware" value={label(snapshot?.support_tier ?? "unknown")} />
      </PanelSection>

      {(error || (snapshot?.blockers.length ?? 0) > 0) && (
        <PanelSection title="Needs attention">
          {error && <PanelSectionRow>{error}</PanelSectionRow>}
          {snapshot?.blockers.map((blocker) => (
            <PanelSectionRow key={blocker.code}>{blocker.message}</PanelSectionRow>
          ))}
        </PanelSection>
      )}

      <PanelSection title="Diagnostics only">
        <PanelSectionRow>
          HDM 0.1 observes the current state. It cannot switch displays, GPUs, or Gamescope.
        </PanelSectionRow>
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={() => void refresh()} disabled={loading}>
            {loading ? "Reading…" : "Refresh"}
          </ButtonItem>
        </PanelSectionRow>
      </PanelSection>
    </>
  );
}

export default definePlugin(() => ({
  name: "Handheld Dock Mode",
  titleView: <div className={staticClasses.Title}>Handheld Dock Mode</div>,
  content: <Content />,
  icon: <MonitorIcon />,
  onDismount() {},
}));
