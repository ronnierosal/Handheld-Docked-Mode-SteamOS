/** Small, controller-first presentation helpers for the Quick Access panel. */

export interface AtAGlanceState {
  mode: string;
  health: string;
  connection: string;
  game: string;
}

/**
 * Keep the first screen to four player-facing facts. Technical evidence stays
 * behind the explicit troubleshooting control.
 */
export function atAGlanceRows(state: AtAGlanceState): Array<[string, string]> {
  return [
    ["Mode", state.mode],
    ["Health", state.health],
    ["Connection", state.connection],
    ["Game", state.game],
  ];
}

export interface JourneyStatusPayload {
  deferred_dock?: { state: string; code: string };
  prepared_docked_idle?: { state: string; code: string };
  safe_undock?: { state: string; code: string };
  unexpected_removal_recovery?: { state: string; code: string };
}

export interface JourneyStatusRow {
  name: string;
  value: string;
  detail: string;
}

const JOURNEY_STATES: Record<string, Record<string, [string, string]>> = {
  deferred_dock: {
    deferred: ["Waiting for game to close", "A player request remains evidence only."],
    eligible: ["Fresh idle evidence", "A future transition owner must revalidate."],
    cancelled: ["Cancelled", "No dock request remains."],
    expired: ["Expired", "A new player request is required."],
    invalidated: ["Needs revalidation", "The prior dock evidence changed or became stale."],
    rejected: ["Not available", "A direct request needs a verified running game."],
  },
  prepared_docked_idle: {
    not_yet_stable: ["Stabilizing", "Fresh idle evidence has not matured yet."],
    prepared: ["Prepared evidence", "A future owner must still revalidate."],
    invalidated: ["Needs revalidation", "Prepared evidence changed or became stale."],
  },
  safe_undock: {
    ready_for_revalidation: ["Needs revalidation", "This is not a physical-unplug approval."],
    not_ready: ["Not ready", "Current Safe Undock evidence does not meet the gate."],
    evidence_insufficient: ["Evidence incomplete", "Collect fresh supervised evidence before deciding."],
    invalidated: ["Needs revalidation", "The Safe Undock evidence changed or became stale."],
  },
  unexpected_removal_recovery: {
    portable_fallback_verified: ["Portable fallback observed", "This does not claim hardware recovery or game survival."],
    recovery_incomplete: ["Recovery incomplete", "Handheld fallback evidence is incomplete."],
    needs_supervised_diagnosis: ["Needs supervised diagnosis", "Evidence is unknown, stale, or contradictory."],
  },
};

export function journeyStatusRows(
  journey: JourneyStatusPayload | undefined,
): JourneyStatusRow[] {
  const rows: Array<[keyof JourneyStatusPayload, string]> = [
    ["deferred_dock", "Dock request"],
    ["prepared_docked_idle", "Prepared state"],
    ["safe_undock", "Safe Undock evidence"],
    ["unexpected_removal_recovery", "Recovery"],
  ];
  return rows.map(([key, name]) => {
    const value = journey?.[key];
    const presentation = value && JOURNEY_STATES[key][value.state];
    return presentation
      ? { name, value: presentation[0], detail: presentation[1] }
      : {
        name,
        value: "Not connected",
        detail: "This local classifier is not yet wired into read-only snapshot delivery.",
      };
  });
}

/** State reset used before returning controller focus to the compact status. */
export function compactStatusPanels(): {
  showDiagnostics: false;
  showJourneyDetails: false;
} {
  return { showDiagnostics: false, showJourneyDetails: false };
}

/**
 * Steam can otherwise send controller focus to the QAM Back control after a
 * long panel collapses. Focus a native in-panel control after the owning panel
 * has been scrolled back to its first row.
 */
export function restoreQuickAccessFocus(
  findFirstControl: () => HTMLElement | null,
): boolean {
  const control = findFirstControl();
  if (!control) {
    return false;
  }
  control.focus({ preventScroll: true });
  return true;
}
