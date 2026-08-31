# Authoritative roadmap

This roadmap reconciles the product north star with the behavior present on
`main`. Product intent does not constitute executable or hardware evidence.
Detailed work items remain in [Backlog](BACKLOG.md); completed hardware
observations remain in the dated validation records.

## Evidence vocabulary

HDM uses these labels consistently:

- **Designed:** documented, but no executable proof.
- **Implemented:** code and deterministic tests exist.
- **Simulated:** replay or failure-injection tests pass without hardware.
- **Installed:** the exact built artifact is present on a device.
- **Hardware tested:** a bounded supervised test produced captured evidence.
- **Verified:** all acceptance criteria for the stated combination passed.
- **Certified:** verified behavior is supported for a named hardware/software
  profile and version range.

No broader label may be inferred from a narrower one.

## Current baseline: 0.2.0 on `main`

| Capability | Current evidence | Remaining gate |
|---|---|---|
| Decky-native plugin lifecycle and typed RPC | Implemented and hardware tested | Release packaging/publishing is separate. |
| Read-only host, DRM, Gamescope, game-scope, PCI, USB4, and G1 discovery | Implemented and hardware tested on Ally X/G1 | Revalidate after material SteamOS/kernel changes. |
| Exact G1 DRM/audio clients and storage blockers | Implemented and hardware tested read-only | Guarded signaling remains simulated and requires supervised proof. |
| Portable inference | Implemented and hardware tested | Other presentation modes remain unverified in native HDM. |
| Backend login1 sleep inhibitor | Implemented and hardware tested | It prevents suspend but cannot alone preserve Steam presentation. |
| Steam-native preflight blocker | Implemented; lifecycle and blocking behavior hardware tested | Corrected persistent warning dialog still needs one supervised visible proof. |
| Adaptive polling and discovery timings | Implemented and hardware tested | Continue measuring rather than assuming latency targets. |
| Redacted support-bundle preview/token/save | Implemented and simulated | Controller-visible preview and save acceptance remain pending. |
| Display/GPU transitions | Durable guarded orchestrator, boot-scoped Gamescope shim/config store, reversible conflict-aware drop-in manager, fixed user-service command boundary, presentation mechanism, Decky-native preparation, and unwired supervised transition facade implemented and simulated | Decky transition controls, startup recovery wiring, and hardware proof remain; preparation cannot restart Gamescope. |
| Process release/termination | Approval/classification, redacted Decky inspect/confirm flow, guarded facade, Linux pidfd adapter, mandatory re-scan runner, root-owned durable pre-signal journal, and no-repeat startup recovery implemented and simulated | Supervised disposable-process proof remains. |
| Physical G1 live removal | Unsupported | A separate teardown experiment must prove it safe before capability enablement. |
| Typed placement/workflow/capability and journal contracts | Implemented and unit tested | Decky request facade and mechanism wiring remain gated. |
| Atomic fixed-path transition journal store | Implemented and unit tested; constructed for process release | Presentation/sleep orchestration wiring and supervised persistence proof remain. |
| Transition snapshot replay and failure injection | Implemented and simulated | No production display/GPU mechanism endpoint exists. |
| Remote read-only capture harness | Implemented and hardware tested unprivileged | Its fixed root read-only mode is locally verified but unavailable on the current Ally because non-interactive sudo is refused. Neither mode can observe the Decky-owned sleep lease. |
| Guarded process-release approvals | Implemented and simulated in Decky-native flow | Supervised disposable-process proof remains. |
| Process-release signal/re-scan runner, audit, and journal | Implemented and simulated | Supervised mechanism proof remains; hardware removal authority is always false. |
| Exact-instance Linux pidfd signal adapter | Implemented, unit tested, and guarded by Decky orchestration | Supervised disposable-process proof remains. |
| Canonical sleep/disconnect reducer + durable coordinator | Implemented and simulated, delivery-independent | Game/save/removal/display/sleep mechanisms, Decky wiring, and supervised proof remain. |
| Independent game compatibility dimensions and review gate | Implemented and unit tested, pure schema only | Collection UI, persistence, intentional hardware tests, and catalog publication remain. |
| Temporary verbose diagnostic logging policy | Implemented and unit tested, dormant | Decky UI/RPC wiring and controller-visible acceptance remain. |
| Optional troubleshooting overlay | Implemented and frontend tested, off by default | Controller-visible hardware acceptance remains. |
| Exact Steam-scope AppID extraction | Implemented and unit tested, internal read-only | Process-tree/title/Proton identity and public schema design remain. |
| Independent hardware capability catalog and review gate | Implemented and unit tested, pure schema only | Persistence, collection UI, and intentional capability tests remain. |
| Reduced transition/compatibility support context | Implemented and privacy tested, dormant optional input | Live owners and controller-visible preview acceptance remain. |
| Compatibility Test Mode session policy | Implemented and simulated, dormant | Hardware observation/mechanism adapters, UI, persistence, and reviewed tests remain. |
| Secure support-submission approval/protocol | Implemented and unit tested, dormant | Fixed TLS client adapter is unwired; Cloudflare Worker/R2 deployment, endpoint configuration, abuse controls, and UI remain. |

## Required architecture corrections

The expanded product model is accepted with these boundaries:

1. **Observed placement and workflow phase remain separate.** Portable,
   Docked-iGPU, Boosted Handheld, and Docked-eGPU describe verified render and
   presentation placement. Connecting, PreparingToDisconnect,
   SleepPendingDisconnect, ReturningToPortable, ActionRequired, and Failure are
   workflow phases. A phase must not overwrite observed hardware truth.
2. **Capabilities are profile data, not scattered conditionals.** Host and eGPU
   profiles conservatively expose support for display, audio, controller,
   sleep, and removal mechanisms. Unknown profiles inherit no mutation rights.
3. **The transition engine owns every mutation.** Manual, automatic, sleep,
   recovery, and future game-restart requests use one journaled
   TRY/OBSERVE/VERIFY/COMMIT engine with bounded recovery.
4. **Game identity is independent evidence.** `game_state=running` remains the
   safety minimum; AppID, title, process tree, Proton, and rendering GPU are
   additional typed observations and may each be unknown.
5. **Compatibility records never self-certify.** Game and hardware test results
   require intentional review before promotion to Verified or Certified.

## Safety conflict: current G1 removal

The desired one-press flow ends with a physical eGPU disconnect followed by
automatic sleep. That flow is not currently available for the certified G1
profile: prior teardown evidence includes AMDGPU removal stalls, and
[Safety invariant 10](SAFETY_INVARIANTS.md) requires internal restoration and
shutdown before disconnect.

The eventual workflow must therefore branch on an explicit removal capability:

- `live_removal_verified`: the engine may verify SafeToDisconnect, wait for
  removal, recover Portable, and continue the original sleep request.
- `shutdown_before_disconnect`: the engine may prepare internal state and offer
  a shutdown-first flow, but must not claim live removal is safe.
- `untested`, `unknown`, or `known_issue`: fail closed and provide diagnostics.

The GPD G1 remains `shutdown_before_disconnect`/known issue until a separately
approved supervised experiment proves otherwise.

## Ordered roadmap

### R0 — Close current installed acceptance gaps

- Prove the corrected Steam warning is visible and persistent during one
  supervised blocked Sleep request.
- Prove controller-visible support preview and exact token-approved save.
- Record installed artifact identity and redacted before/after evidence.

Exit: warning and support UI are hardware tested without suspend, display
mutation, process signaling, or eGPU removal.

### R1 — Read-only control-plane foundation

**Status:** IMPLEMENTED AND SIMULATED — typed contracts, bounded journal schema,
fake clock/mechanisms, snapshot replay, asynchronous-event policy, and remote
read-only capture are implemented. The installed-device capture path has a
read-only hardware proof; no transition mechanism is enabled.

- Add typed placement state, workflow state, request intent, capability records,
  transition plans, deadlines, structured failures, and recovery outcomes.
- Add a durable, bounded, privacy-safe transaction journal contract.
- Add deterministic snapshot replay and a fake clock/mechanism harness.
- Replay partial ordering, stale evidence, timeouts, unexpected unplug,
  controller loss, and recovery failure.
- Add remote-safe capture tooling that performs observation only.

Exit: pure policy and simulator prove state/phase separation and fail-closed
behavior. R1 introduced no production mutation endpoint; R2 owns the later
guarded process-release boundary.

### R2 — Guarded non-game eGPU client release

**Status:** IMPLEMENTED AND SIMULATED — backend-owned preview/token/revalidation,
typed signal/re-scan flow, deadlines, privacy-safe audit, root-owned durable
pre-signal journaling, no-repeat startup recovery, and the guarded application
facade are composed into Decky-native inspect/confirm/execute/acknowledge RPCs.
Private graceful evidence remains behind an opaque, expiring, single-use force
receipt. No PID, signal, command, or path comes from the frontend.

- Generate backend-owned previews for exact eligible process instances.
- Bind short-lived single-use approval tokens to candidate set, device identity,
  resources, and observation generation.
- Revalidate before each bounded graceful signal; re-observe after each action.
- Keep force closure behind a second explicit approval.
- Never signal protected, system, other-user, storage, or unknown clients.

Exit: unit/replay/PID-reuse/failure-injection tests pass, followed by supervised
disposable-process validation. This does not enable physical removal.

### R3 — Manual verified transition engine and recovery

**Status:** DURABLE GUARDED ORCHESTRATOR IMPLEMENTED AND SIMULATED — a one-step
manual Portable↔Docked-eGPU plan is produced only from exact runtime profile,
device/display binding, game, display/render, and source-rollback evidence. A
two-minute single-use backend permit can authorize one explicitly confirmed
Experimental Ally/G1 plan without promoting the capability. The engine
re-observes before apply, journals before mutation, verifies within deadlines,
recovers after failure or a non-durable commit, and handles interrupted
journals without resuming the target request. No active presentation mechanism,
Decky construction, or RPC exists. The first packaged Gamescope shim/config
boundary is implemented and simulated but remains inactive: it installs no
override and cannot restart Gamescope. Exact Gamescope-owner resolution and a
fixed root-to-user command runner are also implemented and unwired; no plugin
path invokes the runner. Reversible fixed drop-in management is simulated and
fails closed on competing `PATH` ownership, including eGPUBridge. The dormant
presentation mechanism composes these parts with immediate config rollback on a
synchronous restart failure; the orchestrator still independently verifies or
recovers the observed placement. Approval-gated integration preparation is also
simulated; it can install/reload/verify without restarting Gamescope and rolls
back a new drop-in on failure.

- Implement one idempotent Portable/Docked transition path with journal,
  precondition re-observation, verification, rollback, and crash recovery.
- Restore a known-good internal display path before any shutdown/removal advice.
- Treat game-running or unknown game state as a blocker whenever Gamescope would
  restart.

Exit: simulation passes first; then supervised Ally X/G1/TV testing with the G1
connected naturally and no live unplug.

### R4 — Canonical sleep request orchestration

**Status:** COORDINATOR IMPLEMENTED AND SIMULATED — Steam-menu and physical
button sources enter one generation-bound service; request expiry, consent/save
branching, process-release routing, removal capability, independent removal
readiness, Portable recovery, original-request continuation, fresh verification
samples, append-only persistence, exact acknowledgement, and fail-closed restart
recovery are covered. No live sleep mechanism or sleep-continuation RPC is
enabled.

- Normalize Steam menu and physical-button attempts into one request intent
  where the platform exposes a verified interception mechanism.
- Obtain consent before closing a game; add save capability warnings without
  claiming universal autosave.
- Release only classified clients, verify final state, and choose the
  profile-specific removal/shutdown branch.
- Resume the original sleep request only when its complete preconditions are
  verified and the request has not expired or been cancelled.

Exit: simulator covers every branch. G1 certification remains limited by its
removal capability.

Composition status: guarded process release is now a child step of the same
sleep transaction journal in the application/simulation layer. It does not run
two authoritative journals or drop pre-signal persistence. Decky sleep delivery
and live mechanisms remain gated.

### R5 — Unexpected-undock recovery

**Status:** PURE EVENT POLICY IMPLEMENTED — unsolicited and sleep-pending cable
loss both route only to Portable recovery; no raw topology event can continue
sleep. Duplicate Portable events observe stability and unknown placement fails
closed. Display/audio/controller recovery mechanisms remain designed only.

- Distinguish unsolicited loss from an expected SleepPendingDisconnect event.
- Restore internal display, audio, and controls; verify Portable; never sleep
  after an unsolicited unplug.

Exit: deterministic replay plus a separately approved hardware test. Any test
that can strand SSH remains supervised.

### R6 — Docked-iGPU research and game-aware launch policy

- Complete the existing read-only experiment and prove unchanged Gamescope and
  game identity, iGPU rendering, and TV presentation.
- After natural game exit, select G1 for subsequent launches and verify the
  actual render GPU.
- Add optional same-AppID restart only after graceful close, save policy, loop
  prevention, relaunch, and fallback are independently proven.

Exit: each game/profile result is recorded in both eGPU-handoff and save/sleep
dimensions. Docked-iGPU remains experimental until real proof exists.

### R7 — Controller and audio handoff

**Status:** PURE POLICY IMPLEMENTED — typed observations and controller/audio
decisions preserve verified fallbacks, separate promotion from suppression, and
gate optional disconnect/power-off independently. Real Ally/G1 capabilities
remain Unknown/Experimental; no observation/mechanism adapter or RPC exists.

- Add profile capabilities and independently observable input/audio state.
- Preserve a usable fallback before suppressing built-in controls or changing
  audio output.
- Treat controller power-off as optional per-controller capability.

Exit: rollback and disconnect-loss tests pass before certification.

### R8 — Diagnostics, compatibility, and support expansion

**Status:** PARTIAL POLICY IMPLEMENTED — independent eGPU-handoff and save/sleep
dimensions, exact-profile evidence, and intentional human-reviewed promotion
gates are unit tested. Explicit opt-in verbose logging durations, expiry,
rotation, and reboot/reset behavior are also unit tested. No collection UI,
persistence, publication, or verbose RPC is enabled.

- Add an opt-in overlay and bounded verbose logging with a maximum TTL that
  cannot survive reboot.
- Maintain the game schema/developer guidance and add the hardware catalog schema.
- Expand previewable support bundles and compatibility test mode.
- Design Cloudflare Worker/private R2 submission separately with explicit
  upload consent, validation, rate limits, and retention.

Exit: privacy/security tests pass; no client credentials or silent upload.

### R9 — Broader hardware support

- Add profiles one combination at a time.
- Make non-eGPU display, controller, and audio features independently useful.
- Never promote unknown hardware through similarity alone.

## Smallest safe next milestone

Unattended-safe R1 policy/replay, guarded process-release implementation,
canonical sleep policy/coordinator, compatibility policy, temporary logging
policy, and the optional overlay are complete. The next release-facing gates are
R0's supervised controller-visible warning/support-preview acceptance and R2's
separate supervised disposable-process validation.

Without physical supervision, continue implementation, simulator, schema, UI,
and recovery work but do not deploy or invoke process signals,
display/GPU/audio/controller mutation, original-sleep continuation, reboot,
suspend, or physical-removal actions. The first future live presentation
transition remains R3 and requires its documented supervised rollback tests.
