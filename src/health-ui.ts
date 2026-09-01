import type { SnapshotPayload } from "./backend";

type HealthState = NonNullable<SnapshotPayload["health"]>["state"];

export function healthStatusLabel(
  health: { state: HealthState } | undefined,
  loading = false,
): string {
  if (loading) {
    return "Checking…";
  }
  switch (health?.state) {
    case "ready":
      return "Ready";
    case "recovering":
      return "Recovering";
    case "degraded":
      return "Degraded";
    case "attention_required":
      return "Needs attention";
    default:
      return "Unavailable";
  }
}
