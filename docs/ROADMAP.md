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
| Read-only host, DRM, Gamescope, game-scope, PCI, USB4, and G1 discovery | Implemented and hardware tested on Ally X/G1; exact DMI tuple, bound-driver topology, backend identity binding, and typed capability diagnostics are locally regression tested | Revalidate the stricter matcher and diagnostic presentation on hardware after material firmware/SteamOS/kernel changes. |
| Exact G1 DRM/audio clients and storage blockers | Implemented and hardware tested read-only | Guarded signaling remains simulated and requires supervised proof. |
| Portable inference | Implemented and hardware tested | Other presentation modes remain unverified in native HDM. |
| Backend login1 sleep inhibitor | Implemented and hardware tested | It prevents suspend but cannot alone preserve Steam presentation. |
| Steam-native preflight blocker | Implemented; lifecycle and blocking behavior hardware tested | Corrected persistent warning dialog still needs one supervised visible proof. |
| Adaptive polling and discovery timings | Implemented and hardware tested | Continue measuring rather than assuming latency targets. |
| Redacted support-bundle preview/token/save | Implemented and simulated; includes bounded categorical peripheral observation state when available | Controller-visible preview and save acceptance remain pending. |
| Display/GPU transitions | Durable guarded orchestrator, boot-scoped Gamescope shim/config store, reversible conflict-aware drop-in manager, fixed user-service command boundary, presentation mechanism, Decky-native preparation, and unwired supervised transition facade implemented and simulated | Decky transition controls, startup recovery wiring, and hardware proof remain; preparation cannot restart Gamescope. |
| Docked-iGPU promotion/recovery path | Durable transition path plus bounded natural-exit watcher, serialized lifecycle, non-authorizing preview composition, and single-owner async driver are implemented and simulated; production runs the watcher in no-preview mode and exposes identity-free status/acknowledgement | Hardware proof, production read-only preview construction, and separately gated confirmation/execution remain. |
| Process release/termination | Approval/classification, redacted Decky inspect/confirm flow, guarded facade, Linux pidfd adapter, mandatory re-scan runner, root-owned durable pre-signal journal, and no-repeat startup recovery implemented and simulated | Supervised disposable-process proof remains. |
| Physical G1 live removal | Unsupported | A separate teardown experiment must prove it safe before capability enablement. |
| Typed placement/workflow/capability and journal contracts | Implemented and unit tested | Decky request facade and mechanism wiring remain gated. |
| Atomic fixed-path transition journal store | Implemented and unit tested; constructed for process release | Presentation/sleep orchestration wiring and supervised persistence proof remain. |
| Transition snapshot replay and failure injection | Implemented and simulated | No production display/GPU mechanism endpoint exists. |
| Remote read-only capture harness | Implemented and hardware tested unprivileged | Its fixed root read-only mode is locally verified but unavailable on the current Ally because non-interactive sudo is refused. Neither mode can observe the Decky-owned sleep lease. |
| Guarded process-release approvals | Implemented and simulated in Decky-native flow | Supervised disposable-process proof remains. |
| Process-release signal/re-scan runner, audit, and journal | Implemented and simulated | Supervised mechanism proof remains; hardware removal authority is always false. |
| Exact-instance Linux pidfd signal adapter | Implemented, unit tested, and guarded by Decky orchestration | Supervised disposable-process proof remains. |
| Canonical sleep/disconnect reducer + durable coordinator | Implemented and simulated, delivery-independent | Save/removal/display/sleep mechanisms, Decky wiring, and supervised proof remain. |
| Exact-identity guarded game-close child | Implemented and simulated, mechanism-injected | Production SteamOS close mechanism, Decky delivery, and supervised proof remain. |
| Exact-recipe verified game-save child | Implemented and simulated, proof/mechanism-injected | Reviewed production recipes, proof/mechanism adapters, Decky delivery, and per-game hardware proof remain. |
| Backend-owned canonical sleep delivery facade | Implemented and unit tested, dormant | Decky RPC/UI wiring, physical-button interception, all directive mechanisms, and supervised proof remain. |
| Independent game compatibility dimensions and review gate | Implemented and unit tested, with dormant fixed-path atomic persistence and a backend-only reviewed-evidence transaction service | Collection UI, production plugin construction, intentional hardware tests, and catalog publication remain. |
| Temporary verbose diagnostic logging | Policy and Decky controller flow implemented and simulated; explicit consent, four bounded durations, status/countdown, disable, sanitization, rotation, and reboot reset are wired | Controller-visible and expiry acceptance remain. |
| Optional troubleshooting overlay | Implemented and frontend tested, off by default | Controller-visible hardware acceptance remains. |
| Exact Steam-scope AppID extraction | Implemented and unit tested, internal read-only | Steam title/version and consumer wiring remain. |
| Private active-game process/runtime evidence | Implemented and unit tested, dormant read-only | Exact Proton version, consumers, Decky wiring, and hardware proof remain. |
| Bracketed game/eGPU render-client correlation | Implemented and unit tested, dormant read-only | Production consumers and hardware comparison with engine evidence remain. |
| Bounded exact DRM engine-activity evidence | Implemented and simulated for independently re-resolved Ally internal and G1 bindings; one-shot shared-window categorical comparison is wired into existing Support Preview | Hardware proof, continuous consumers, and reviewed compatibility use remain. |
| Independent hardware capability catalog and review gate | Implemented and unit tested, with dormant fixed-path atomic persistence and a backend-only reviewed-evidence transaction service | Collection UI, production plugin construction, and intentional capability tests remain. |
| Reduced transition/compatibility support context | Implemented and privacy tested, dormant optional input | Live owners and controller-visible preview acceptance remain. |
| Compatibility Test Mode session policy | Implemented and simulated with dormant exact internal-baseline/external-render collectors, each session-bracketed, an application-only single-session temporary-diagnostics lifecycle that uses backend-owned user context only, and an unwired identity-free status mapper | Plugin construction/UI, persistence, save evidence consumer, trusted hardware runs, and reviewed tests remain. |
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
6. **Performance is a runtime budget.** HDM prefers event-driven observation;
   any required polling has a bounded cadence, does not overlap expensive
   scans, and defers nonessential work during an active game. Telemetry is a
   shared, lightweight evidence source rather than a collection of optimization
   loops.
7. **Health and controls are independent contracts.** Placement does not imply
   a usable display, controller, audio route, or eGPU link. Future physical
   button/controller delivery maps to typed logical requests and enters the
   same transition engine as Decky UI actions.

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
recovery are covered. An exact AppID/scope game-close child now binds explicit
single-use consent to the same parent operation, persists before its injected
mechanism, and advances only after a fresh verified Idle observation. No
production game-close or live sleep mechanism and no sleep-continuation RPC is
enabled. A verified-save child now binds the already-granted close consent to
one exact reviewed recipe and requires an independent new Verified proof before
unlocking close; no production recipe or adapter is present. A dormant delivery
facade now owns request IDs/generations and exposes privacy-safe result/status,
exact operation-bound consent/cancel, recovery, and acknowledgement without
executing any directive.

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
and live mechanisms remain gated. Guarded game close uses the same composition
rule and records no AppID or scope identity in the journal. A
verified-triggerable-autosave game remains blocked unless the save child proves
completion for that exact parent request. The 26-target sleep-child release
bound leaves room for save, close, graceful plus force release, every remaining
sleep stage, and recovery within the 128-entry journal.

Read-only G1 suspend investigation now has a bounded exact-topology PCI
wake-capability/runtime collector in the remote capture payload. It exports
only categorical aggregate evidence and does not identify a wake source or
change any wake/power setting. The same categorical evidence is now included
only in an explicit redacted support-bundle preview, never normal polling.
Actual suspend/resume proof remains a supervised D6 hardware gate; see
[G1 suspend/wake diagnostics](SUSPEND_WAKE_DIAGNOSTICS.md).

### R5 — Unexpected-undock recovery

**Status:** APPLICATION COORDINATOR IMPLEMENTED AND SIMULATED — unsolicited and
exact canonical sleep-pending loss remain distinct, and both route only through
fresh detect/validate/attempt/verify/commit Portable recovery. The coordinator
returns a bounded identity-free trace, uses a separately bounded
Portable-preservation fallback, and rejects stale/unknown evidence. It has no
sleep port: a verified sleep-pending result only requests a later canonical
transaction re-check. Production topology, display/GPU, audio, controller,
Decky, journal/facade, and startup-recovery wiring remain gated. Physical G1
removal remains unsupported. See
[Unexpected-undock recovery coordinator](UNEXPECTED_UNDOCK_RECOVERY.md).

A pure snapshot-delta detector now supplies only exact attach, eGPU-removal,
or external-display-loss candidates. It has no event source or execution
authority: a future watcher must still feed its result into the shared policy
and transition authority. Missing, reused, ambiguous, or unproven loss evidence
is explicitly unverified.

- Distinguish unsolicited loss from an expected SleepPendingDisconnect event.
- Restore internal display, audio, and controls; verify Portable; never sleep
  after an unsolicited unplug.

Exit: deterministic replay is implemented. Production exit still requires the
shared serialized transition authority, reviewed SteamOS event/mechanism
adapters, audio/controller recovery coverage, and a separately approved D6
hardware test on a profile with verified live removal. Any test that can strand
SSH remains supervised; the GPD G1 is not eligible.

### R6 — Docked-iGPU research and game-aware launch policy

**Status:** PARTIAL READ-ONLY FOUNDATION IMPLEMENTED — exact Steam AppID/scope
identity can be enriched with bounded PID/start-time process instances,
parent/launcher relationships, executable basenames, and native-versus-Proton
classification. All exact identity remains private and fail closed; the only
production consumer is the existing user-invoked Support Preview, and no
mutation, relaunch path, or new Decky RPC exists. See
[Active game runtime evidence](GAME_RUNTIME.md). Stable exact game processes can
also be correlated with a complete exact G1 client scan to prove render-node
ownership or absence, but that result deliberately does not claim active
rendering or identify another GPU. A separate bounded DRM `fdinfo` sampler can
now prove that one exact game's engine counters increased on one exact GPU
during a stable sample window. Exact read-only Ally internal and G1 binding
resolvers revalidate their profiles and one render node before sampling. The
existing Support Preview action can now collect one bounded shared-window,
identity-free internal/G1 comparison; either Unknown target remains incomplete
and hardware validation remains absent. The dormant
Compatibility Test Mode collector can consume this proof
only for a
same-AppID internal-GPU baseline and Docked-eGPU observation; it cannot finish,
review, promote, or publish the result.
Exact idle Docked-iGPU can now be previewed and promoted to Docked-eGPU through
the existing experimental approval and durable transition engine, with
Docked-iGPU as the verified rollback target. Automatic natural-game-exit
detection now exists as a bounded read-only one-shot watcher. A serialized
lifecycle owns its private watch, bounded polling, Action Required
acknowledgement, and unload cleanup. Its identity-free inspection always uses
an unconfirmed preview and rejects unexpected transition authority. The
lower-level facade composes the private ready generation with the existing
supervised preview and can consume the watch only after a separate explicit
approval-token issuance; neither layer executes the token. Production now
constructs the watcher, facade, lifecycle, and single-owner async driver in
watch-only mode for the exact Gamescope user. Decky exposes identity-free
status and Action Required acknowledgement, while inspection, approval, and
execution remain absent. The observer polls every five seconds while actively
watching; ineligible checks use a fifteen-second cadence and
skip full discovery when no exact game runs. Watch-only readiness is cleared
after one reporting interval, Gamescope restarts invalidate the exact watch,
and a bounded supervisor recovers transient observer failure. The task closes
on plugin unload. See
[Docked-iGPU workflow](DOCKED_IGPU.md).
The support-preview comparison adds no scheduler, transition approval, or
execution authority and never promotes a compatibility record.

- Complete the existing read-only experiment and prove unchanged Gamescope and
  game identity, iGPU rendering, and TV presentation.
- After natural game exit, select G1 for subsequent launches and verify the
  actual render GPU.
- Add optional same-AppID restart only after graceful close, save policy, loop
  prevention, relaunch, and fallback are independently proven.

Exit: each game/profile result is recorded in both eGPU-handoff and save/sleep
dimensions. Docked-iGPU remains experimental until real proof exists.

### R7 — Controller and audio handoff

**Status:** PURE POLICY AND COMPOSITE PLANNING IMPLEMENTED — versioned private
observations bind semantic generation, fresh sample identity, exact opaque
controller/audio targets, rollback targets, and categorical failures.
Controller/audio decisions preserve verified fallbacks, separate promotion from
suppression, order external disconnect/power-off last, and require verification
after every future step. Each subsystem fails closed independently; changed or
repeated shared evidence emits no steps at all. Partial safe work is distinct
from a fully ready plan. Real Ally/G1 capabilities remain
Unknown/Experimental; no live mechanism adapter or RPC exists. A bounded
read-only sysfs inventory now discovers gamepad and sound-card candidates using
hashed private bindings; absent supervised mapping it reports controller
identity/default audio as unverified and authorizes no steps. See
[Controller and audio handoff foundation](PERIPHERAL_HANDOFF.md). The optional
troubleshooting overlay exposes only the associated categorical mapped/unmapped
diagnostics and remains non-authorizing. Mapping evidence is now typed,
reviewed, and bound to the complete opaque inventory fingerprint; a changed
inventory makes it stale and still cannot verify controller input or audio
output usability.

- Add profile capabilities and independently observable input/audio state.
- Preserve a usable fallback before suppressing built-in controls or changing
  audio output.
- Treat controller power-off as optional per-controller capability.

Exit: rollback and disconnect-loss tests pass before certification.

### R8 — Diagnostics, compatibility, and support expansion

**Status:** PARTIAL DELIVERY IMPLEMENTED — independent eGPU-handoff and save/sleep
dimensions, exact-profile evidence, and intentional human-reviewed promotion
gates are unit tested. Explicit opt-in verbose logging durations, expiry,
rotation, reboot/reset behavior, Decky status/countdown, confirmation, and
disable controls are implemented and simulated. Fixed-path atomic catalog
persistence and backend-only reviewed-evidence transactions are implemented but
remain unconstructed by Decky. No catalog collection UI, publication, or support
upload is enabled.

- Add an opt-in overlay and bounded verbose logging with a maximum TTL that
  cannot survive reboot.
- Maintain the game schema/developer guidance and add the hardware catalog schema.
- Expand previewable support bundles and compatibility test mode.
- Design Cloudflare Worker/private R2 submission separately with explicit
  upload consent, validation, rate limits, and retention.

Exit: privacy/security tests pass; no client credentials or silent upload.

### R9 — Broader hardware support

- **Implemented (catalog boundary):** runtime resolution accepts explicit
  host/eGPU profile definitions rather than central model-specific conditionals.
  Absent or ambiguous catalog matches remain Unknown. The catalog contains only
  the existing Ally X/G1 entries, and new definitions are not certification.
- Add profiles one combination at a time.
- Make non-eGPU display, controller, and audio features independently useful.
- Never promote unknown hardware through similarity alone.

### Later foundation backlog — performance and game experience

These items are intentionally deferred until the safe transition/recovery and
hardware-validation gates above are closed. They must extend the existing core;
they are not authorization for a separate optimizer or launcher.

- Expand the implemented typed health aggregation from placement, session,
  display, storage, and current exact-bridge PCIe link observation (including
  read-only current speed/lane evidence where the kernel exposes it) to
  independently verified controller, audio, link-quality, and recovery
  evidence. **Implemented (optional input):** one independently collected
  peripheral observation now contributes controller/audio health only when it
  proves usable built-in input/current output; incomplete evidence is Attention
  Required and known built-in loss is Degraded. Snapshot wiring remains deferred.
  Current link up/down is neither throughput proof nor removal authority.
- **Implemented (pure contract):** the shared telemetry admission contract
  requires a typed bounded metric set, declared collection interval, measured
  cost, benchmark evidence, and an explicit low-cost budget before a future
  periodic collector could run. It delegates to the existing game-aware runtime
  budget and has no collector, scheduler, Auto TDP, or mutation authority.
  A real collector remains deferred until cost and game-impact measurement are
  recorded for a supported profile.
- **Implemented (pure shortcut policy):** the default verified held **Guide +
  Y** chord maps to the existing controller Safe Undock logical request, which
  remains routed through the ordinary `UNDOCK` transition vocabulary. Add a
  controller-driven delivery adapter only after it can debounce input and call
  the canonical request facade without parallel execution logic.
- **Implemented (pure contract):** mode-profile data keeps display preference
  (including HDR/VRR) separate from game render targets and player experience
  goals. It resolves only exact stable observed modes and has no display,
  GPU, power, audio, controller, or game-setting mechanism authority. Future
  consumers still require capability proof and TRY/VERIFY.
- **Implemented (pure contract):** a reviewed Game Adapter must use typed
  allowlisted settings and exact opaque revisions. Its future mechanism is
  constrained to compare-before-write, backup, atomic staging, validation,
  commit confirmation, and verified rollback on failure. No game adapter,
  config writer, game-setting UI, or frontend authority exists yet.
- Research community-settings licensing/attribution and Steam integration
  boundaries before collecting, redistributing, or presenting recommendations.
- **Implemented (projection only):** transparent action history derives a
  short controller-friendly timeline from the existing bounded HDM event log.
  It stores nothing new and exports only action kind, outcome, code, and time;
  detail fields and correlation IDs stay private. The optional Decky
  troubleshooting view renders at most three entries through a read-only RPC.
  The existing snapshot refresh also records only verified topology candidates
  there; no detection result is a recovery or transition authority.

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
