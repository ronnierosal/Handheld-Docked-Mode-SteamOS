import type { BlockedAttemptWarning } from "./sleep-preflight";

export interface BlockedAttemptDelivery {
  showModal: () => void;
  showFallbackToast: (warning: BlockedAttemptWarning) => void;
}

/**
 * Keep enforcement independent from a particular Decky modal host. A visible
 * fallback is preferable to silently losing the explanation when that host
 * rejects a modal from Steam's transient Power-menu lifecycle.
 */
export function deliverBlockedAttempt(
  warning: BlockedAttemptWarning,
  delivery: BlockedAttemptDelivery,
): "modal" | "fallback" | "unavailable" {
  try {
    delivery.showModal();
    return "modal";
  } catch {
    try {
      delivery.showFallbackToast(warning);
      return "fallback";
    } catch {
      return "unavailable";
    }
  }
}
