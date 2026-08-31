# eGPUBridge feature review for HDM

## Decision rule

HDM is a Decky Loader-native product, not an eGPUBridge rename. eGPUBridge is
evidence for useful behavior, hardware constraints, and failure modes. Features
are reimplemented through HDM's typed observations, policy, transactions, and
native Decky UI; its monolithic backend and legacy UI are not ported.

## Recommended feature selection

| eGPUBridge capability | HDM decision | Target | Reason |
|---|---|---|---|
| DRM, Gamescope, Steam-game, PCI, and USB4 discovery | Keep, redesigned | 0.1 | Required evidence for every later decision; already implemented. |
| Native Decky Quick Access UI and typed RPC | Keep, redesigned | 0.1 | This is HDM's only supported player-facing delivery model. |
| Portable / TV Docked manual switch | Reimplement | 0.2 | Core product workflow; must use one verified transaction engine. |
| Restore Internal recovery | Reimplement | 0.2 | Required rollback and black-screen recovery path. |
| Running-game transition block | Reimplement | 0.2 | Required safety invariant; unknown game state also blocks. |
| eGPU sleep warning and resume observation | Reimplement | 0.2 | The certified Ally X/GPD G1 immediately wakes from attached sleep. |
| Sleep blocking while the G1 is attached | Implemented; live lease/UI validated | 0.2 | A crash-safe login1 lease and Decky warnings are active on the certified Ally X/G1; supervised sleep-request paths remain pending. |
| Exact disconnect readiness report | Read-only core implemented | 0.1/0.2 | Schema 2 now explains exact GPU/audio process clients and mounted/swap storage; transition actions remain 0.2. |
| Close processes using the exact eGPU | New guarded workflow | 0.2 | Addresses stale non-game clients without presenting live unplug as safe. |
| Hot-plug observation and internal failback | Reimplement | 0.2 | Protects the next Gamescope session when the configured eGPU is absent. |
| PCIe/USB4 link-health diagnostics | Reimplement read-only | 0.2 | Useful for the degraded G1 link; not a transition prerequisite by itself. |
| TV ADB, Wake-on-LAN, and input control | Defer, optional adapter | Later | Useful convenience, but separate from safe dock state and not required for 0.2. |
| Recovery hardware hotkeys | Defer | Later | Useful after the transition engine and native UI recovery are proven. |
| GPU telemetry | Consider read-only subset | Later | Helpful but not core to mode correctness. |
| GPU power, fan, clock, or voltage tuning | Do not port initially | Out of scope | Expands hardware risk and needs its own profiles, bounds, watchdog, and rollback. |
| NVIDIA driver installation or removal | Do not port | Out of scope | OS package and driver mutation does not belong in the HDM Decky RPC surface. |
| Physical live G1 PCI/USB4 removal | Do not enable | Unsupported | The validated Ally X/G1 path has produced AMDGPU teardown stalls. |
| Transparent running-game GPU migration | Do not promise | Unsupported | A live graphics device cannot generally migrate between physical GPUs. |

## Sleep guard behavior

The root Decky backend owns a login1 sleep-inhibitor lease while the exact
certified G1 is present. The lease is released when the G1 is verified absent or
the plugin unloads. A crashed plugin must not leave a permanent system inhibitor.

The Decky UI shows a persistent **Sleep blocked** state and explains why:

| Observed state | Behavior |
|---|---|
| G1 absent | Sleep is not blocked by HDM. |
| G1 present, no game using it | Block sleep and warn that this hardware is known to wake immediately; direct the user to Portable, power off, and disconnect the G1. |
| G1 selected for rendering and game state unknown | Block sleep and explain that workload safety is unknown. |
| A game owns the G1 | Hard-block sleep and show the game/eGPU warning. Offer a separate close-game workflow, never an implicit kill. |

The informational attached-G1 warning may offer **Never show again**. That
preference suppresses the repeated explanatory banner only. It does not release
the inhibitor, change a blocker, suppress a destructive-action confirmation, or
turn an unsafe state into an allowed state. The current blocked state remains
visible as a compact status row.

Power-menu interception can improve the warning experience, but it is not the
safety boundary: physical power-button and external sleep requests must still be
covered by the root login1 inhibitor. HDM must test the Decky/Steam UI hook and
the inhibitor independently.

On the validated Ally build, logind reports `HandlePowerKey=ignore`; Steam owns
the visible power-button path. Therefore HDM cannot assume that acquiring a
login1 lock is sufficient. Acceptance requires separate supervised tests for the
Quick Access Sleep action, the physical power button, idle sleep, and direct
login1/system sleep requests, including whether any privileged caller bypasses
inhibitors.

## Close eGPU processes workflow

**Close eGPU Processes** is distinct from **Disconnect eGPU**. It may remove
software blockers, but HDM must re-run every disconnect check afterward and may
still require shutdown.

1. Resolve the exact card and render nodes from the verified eGPU identity.
2. Enumerate `/proc/<pid>/fd` links to only those nodes; never target every DRM
   process.
3. Bind each candidate to PID, UID, command name, process start time, opened
   nodes, and the current eGPU fingerprint.
4. Classify candidates:
   - Steam game: offer **Close game**, then bounded graceful termination.
   - Eligible user process: offer a selected-process or all-eligible close.
   - Gamescope, Steam, Decky, display/session managers, and system processes:
     protected; never kill through this workflow.
   - Storage clients or mounted filesystems: non-overridable blocker because
     forced closure or removal can corrupt data.
5. Preview the exact eligible processes and warn about unsaved work.
6. On approval, send `SIGTERM`, wait for a bounded interval, and re-observe.
7. If an eligible process still holds the same node, offer a second explicit
   **Force close remaining** confirmation before `SIGKILL`.
8. Before either signal, verify the process start time and token-bound snapshot
   to prevent PID reuse or stale approval.
9. Re-run render GPU, active display, running-game, DRM client, audio, storage,
   USB4, and hardware-identity checks. Never claim safe disconnect while any
   required observation is unknown.
10. Audit the preview, approval, each signal, exit result, and final readiness
    result without recording command lines or private paths.

The frontend never submits arbitrary PIDs, signals, commands, or paths. It sends
only a short-lived approval token issued for the backend-computed candidate set.

## Proposed 0.2 slices

1. Expand read-only observations: exact DRM clients and audio/storage users are
   implemented; sleep compatibility and inhibitor capability remain.
2. Add pure policy for sleep eligibility, process classification, and disconnect
   readiness.
3. Add the durable transition journal and manual Portable / TV Docked engine.
4. Add the sleep inhibitor and native warning preferences. Implemented; direct
   sleep-request path validation remains.
5. Add graceful close and separately confirmed force-close for eligible clients.
6. Add supervised Ally X/G1 tests for transitions, sleep attempts, process
   closure, failure injection, and internal recovery.

No slice enables physical live unplug on the certified G1 until a separate
hardware experiment proves teardown reliable.
