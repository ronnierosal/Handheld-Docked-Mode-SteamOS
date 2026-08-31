import { definePlugin, toaster } from "@decky/api";
import {
  ButtonItem,
  PanelSection,
  PanelSectionRow,
  staticClasses,
} from "@decky/ui";
import { useCallback, useEffect, useRef, useState } from "react";

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

const SLEEP_WARNING_KEY = "hdm.hideAttachedG1SleepWarning";

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
  const [sleepWarningHidden, setSleepWarningHidden] = useState(
    () => localStorage.getItem(SLEEP_WARNING_KEY) === "1",
  );
  const warningToastShown = useRef(false);
  const inactiveToastShown = useRef(false);

  const refresh = useCallback(async (quiet = false) => {
    if (!quiet) {
      setLoading(true);
      setError("");
    }
    try {
      setPayload(await getSnapshot());
    } catch {
      setError("Read-only snapshot unavailable. Check the Decky log for details.");
    } finally {
      if (!quiet) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
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

  return (
    <>
      <PanelSection title="Observed state">
        <DiagnosticRow name="Mode" value={loading ? "Reading…" : label(payload?.inference.mode ?? "unknown")} />
        <DiagnosticRow name="Game" value={label(snapshot?.game_state ?? "unknown")} />
        <DiagnosticRow name="Render GPU" value={renderer ? label(renderer.role) : "Unknown"} />
        <DiagnosticRow name="Active display" value={display ? label(display.kind) : "Unknown"} />
        <DiagnosticRow name="Hardware" value={label(snapshot?.support_tier ?? "unknown")} />
      </PanelSection>

      {sleepGuard?.required && (
        <PanelSection title="Sleep protection">
          <DiagnosticRow
            name="Sleep"
            value={sleepGuard.active ? "Blocked while G1 attached" : "Protection inactive"}
          />
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
        </PanelSection>
      )}

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
          HDM 0.2 observes the current state and blocks sleep while the G1 is attached. It cannot switch displays, GPUs, Gamescope, or close processes.
        </PanelSectionRow>
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={() => void refresh()} disabled={loading}>
            {loading ? "Reading…" : "Refresh"}
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
    </>
  );
}

export default definePlugin(() => ({
  name: "Handheld Dock Mode",
  titleView: <div className={staticClasses.Title}>Handheld Dock Mode</div>,
  content: <Content />,
  icon: <MonitorIcon />,
  alwaysRender: true,
  onDismount() {},
}));
