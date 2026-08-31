import type { SnapshotPayload } from "./backend";


export interface DiagnosticOverlayRow {
  name: string;
  value: string;
}

function humanize(value: string): string {
  return value.replaceAll("_", " ");
}

function yesNoUnknown(value: boolean | null): string {
  return value === true ? "yes" : value === false ? "no" : "unknown";
}

export function diagnosticOverlayRows(
  payload: SnapshotPayload | null,
): DiagnosticOverlayRow[] {
  if (!payload) {
    return [];
  }
  const { snapshot } = payload;
  const renderer = snapshot.gpus.find((gpu) => gpu.selected_for_render === true);
  const externalGpu = snapshot.gpus.find((gpu) => gpu.role === "external");
  const externalDisplay = snapshot.displays.find((display) => display.kind === "external");
  const disconnect = snapshot.disconnect_readiness;
  const rows: DiagnosticOverlayRow[] = [
    { name: "Observed mode", value: humanize(payload.inference.mode) },
    { name: "Snapshot schema", value: String(snapshot.schema_version) },
    { name: "Device profile", value: snapshot.host_profile },
    { name: "Support tier", value: humanize(snapshot.support_tier) },
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
      value: "off · control not enabled in this build",
    },
  ];
  disconnect.clients.forEach((client, index) => {
    rows.push({
      name: `Client ${index + 1}`,
      value: `${client.name} · ${humanize(client.kind)} · ${client.resources.map(humanize).join(", ")}`,
    });
  });
  return rows;
}
