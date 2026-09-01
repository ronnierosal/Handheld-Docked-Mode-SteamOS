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
