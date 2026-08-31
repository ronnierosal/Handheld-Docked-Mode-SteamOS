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
  const disconnect = snapshot?.disconnect_readiness;
  const disconnectStatus = loading
    ? "Reading…"
    : !disconnect?.applicable
      ? "eGPU not connected"
      : !disconnect.scan_complete
        ? "Scan incomplete — blocked"
        : disconnect.ready
          ? "Ready"
          : "Blocked";

  return (
    <>
      <PanelSection title="Observed state">
        <DiagnosticRow name="Mode" value={loading ? "Reading…" : label(payload?.inference.mode ?? "unknown")} />
        <DiagnosticRow name="Game" value={label(snapshot?.game_state ?? "unknown")} />
        <DiagnosticRow name="Render GPU" value={renderer ? label(renderer.role) : "Unknown"} />
        <DiagnosticRow name="Active display" value={display ? label(display.kind) : "Unknown"} />
        <DiagnosticRow name="Hardware" value={label(snapshot?.support_tier ?? "unknown")} />
      </PanelSection>

      <PanelSection title="Disconnect readiness">
        <DiagnosticRow name="Status" value={disconnectStatus} />
        {disconnect?.applicable && (
          <DiagnosticRow
            name="Resource clients"
            value={String(disconnect.clients.length)}
          />
        )}
        {disconnect?.clients.map((client) => (
          <PanelSectionRow key={client.instance_id}>
            <div>
              <div>{client.name} · PID {client.pid} · {label(client.kind)}</div>
              <div style={{ fontSize: "0.85em", opacity: 0.7 }}>
                {client.resources.map(label).join(", ")} · {client.reason}
              </div>
            </div>
          </PanelSectionRow>
        ))}
        {(disconnect?.storage_devices ?? 0) > 0 && (
          <DiagnosticRow
            name="eGPU storage"
            value={disconnect?.storage_in_use ? "In use — blocked" : "Not mounted"}
          />
        )}
        {disconnect?.error && <PanelSectionRow>{disconnect.error}</PanelSectionRow>}
        <PanelSectionRow>
          Read-only evidence. HDM did not close processes or disconnect hardware.
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

      <PanelSection title="Diagnostics only">
        <PanelSectionRow>
          HDM 0.1 observes the current state. It cannot switch displays, GPUs, Gamescope, or close processes.
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
