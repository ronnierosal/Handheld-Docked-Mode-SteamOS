import { beforePatch, findModuleExport } from "@decky/ui";

import type { SteamSuspendAdapter } from "./sleep-preflight";
import {
  createSteamSuspendAdapter,
  isSteamSuspendStore,
} from "./steam-suspend-adapter";

export function createDeckySteamSuspendAdapter(): SteamSuspendAdapter | null {
  return createSteamSuspendAdapter(
    () => findModuleExport((candidate) => isSteamSuspendStore(candidate)),
    (object, property, handler) => beforePatch(object, property, handler),
  );
}
