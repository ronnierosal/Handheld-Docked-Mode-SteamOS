import type { SteamSuspendAdapter } from "./sleep-preflight";

export interface SteamSuspendStore {
  BlockSuspendAction(): unknown;
  OnSuspendRequest(...args: unknown[]): unknown;
  RequestSleep(...args: unknown[]): unknown;
}

export interface PatchHandle {
  unpatch(): void;
}

export type BeforePatch = (
  object: object,
  property: string,
  handler: (args: unknown[]) => void,
) => PatchHandle;

export function isSteamSuspendStore(value: unknown): value is SteamSuspendStore {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Partial<SteamSuspendStore>;
  return (
    typeof candidate.BlockSuspendAction === "function"
    && typeof candidate.OnSuspendRequest === "function"
    && typeof candidate.RequestSleep === "function"
  );
}

export function createSteamSuspendAdapter(
  resolveStore: () => unknown,
  patchBefore: BeforePatch,
): SteamSuspendAdapter | null {
  let store: SteamSuspendStore;
  try {
    const candidate = resolveStore();
    if (!isSteamSuspendStore(candidate)) {
      return null;
    }
    store = candidate;
  } catch {
    return null;
  }

  return {
    acquireBlocker(): () => void {
      const nativeRelease = store.BlockSuspendAction.call(store);
      if (typeof nativeRelease !== "function") {
        throw new Error("Steam returned an invalid suspend-blocker lease");
      }
      let released = false;
      return () => {
        if (released) {
          return;
        }
        released = true;
        nativeRelease();
      };
    },

    observeSuspendRequests(handler: () => void): () => void {
      const patch = patchBefore(store, "OnSuspendRequest", () => handler());
      let unpatched = false;
      return () => {
        if (unpatched) {
          return;
        }
        unpatched = true;
        patch.unpatch();
      };
    },
  };
}
