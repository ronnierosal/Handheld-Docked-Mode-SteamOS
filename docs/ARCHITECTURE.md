# Architecture

## Design rule

Separate policy from mechanism from hardware.

```text
Decky UI / diagnostics CLI
            |
      application services
       /             \
read-only snapshot   transition engine (0.2+)
       \             /
        pure domain policy
          /        \
 SteamOS adapters  hardware profiles
```

## Domain

`backend/hdm/domain` owns immutable observations, user-facing mode inference,
support tiers, blockers, and future transition vocabulary. It performs no I/O and
does not know Decky, sysfs, systemd, subprocesses, or hardware commands.

Physical connection, display target, render GPU, Gamescope, workload, support,
and health are separate axes. `OperatingMode` is derived only from an exact
combination of verified axes.

The target model also keeps **placement** separate from **workflow phase**.
Portable, Docked-iGPU, Boosted Handheld, and Docked-eGPU are placement results;
Connecting, PreparingToDisconnect, SafeToDisconnect, ReturningToPortable,
SleepPendingDisconnect, ActionRequired, and Failure describe a request's
progress. The typed split, durable journal, deterministic replay, and guarded
runtime orchestrator are implemented; mechanism wiring remains experimental and
uninstalled. See [Authoritative roadmap](ROADMAP.md).

The first control-plane slice now defines typed placement and workflow states,
request/plan/deadline/failure/recovery values, conservative host/eGPU capability
composition, and a strict bounded transaction-journal schema. Decky now uses the
fixed-path store for guarded process release; the presentation runtime
orchestrator remains unconstructed, so no production display/GPU transition
endpoint is enabled.

The guarded-process backlog has an internal approval service that issues
single-use tokens for backend-discovered eligible instances and requires a fresh
exact revalidation before returning internal signal targets. Graceful and force
approvals are distinct, and force requires prior graceful-attempt evidence.
Decky exposes the service only through redacted inspect/confirm/token/acknowledge
operations; the frontend never supplies a process target or signal.

A deterministic process-release runner exercises either a fake or narrow real
signal port. It re-scans after every action, revalidates the remaining approved
subset before every next action, enforces per-signal deadlines, and exports an
identity-free audit. With a journal port, every event is persisted and
`step_started` is durable before signaling. Restart recovery never repeats a
signal; it terminalizes the operation as Action Required. Clearing software
clients never sets hardware-removal authority. See
[Guarded eGPU process-release contract](PROCESS_RELEASE.md).

Each release operation owns a generated operation ID and records its request,
fresh observation, approval validation, plan, per-target typed signal steps,
re-scans, and terminal result in the shared transition journal. Tokens and
process/hardware identity never enter the exported journal.

The journal's fixed-path file adapter enforces atomic append-only
progress for one operation, no-follow/exclusive temporary creation, byte bounds,
file and directory synchronization, and matching-terminal-only cleanup. Decky
constructs it for process release under the separately hardened fixed root-owned
mode-0700 `/var/lib/handheld-dock-mode` state directory; the user-owned Gamescope
config root is not control-state authority. See
[Durable transition journal](TRANSITION_JOURNAL.md).

The guarded runtime orchestrator uses that journal contract for real mechanism
ports. It revalidates the exact profile/device/display binding and idle game
immediately before every attempt, persists `step_started` before the mechanism
call, polls fresh observations only inside the step deadline, commits only a
verified destination, and recovers to the source after apply, verification, or
commit-persistence failure. Startup recovery distinguishes pre-mutation
interruption from a persisted attempted step and never resumes the original
request automatically. The mechanism port is still unwired.

Runtime observation generations hash the complete semantic snapshot but exclude
the collection timestamp. Two unchanged polls can therefore satisfy a
preview/approval boundary, while any game, GPU, display, Gamescope, readiness,
sleep-guard, client, or blocker change invalidates the generation.
Each observation also carries a separate per-scan sample ID that includes the
collection timestamp. Operations such as process signaling use that sample ID
to prove a new scan occurred even when its semantic facts are unchanged. A
semantic generation is never treated as proof of a fresh scan.

The dormant presentation mechanism now composes fresh binding/profile
revalidation, exact Gamescope-user revalidation, reversible integration status,
daemon-reload, fixed-unit verification, atomic target configuration, and a
non-blocking fixed-target restart. It rechecks the user before and after staging
the config. A synchronous restart failure restores the currently observed
source config immediately; a rollback-write failure is reported separately.
The orchestrator skips a redundant recovery restart when a fresh observation
already proves the source placement. Neither component is constructed by Decky.

A separate preparation service owns reversible integration activation.
It issues a maximum-two-minute, single-use approval only from a verified
Portable, idle, healthy Gamescope observation and binds it to the semantic
generation, exact Gamescope user, and SHA-256 of the shim plus expected drop-in.
Execution re-observes all evidence, installs the fixed file, rechecks the
fingerprint/user, reloads the fixed user manager, and verifies the fixed unit.
It never restarts Gamescope. A reload/verification failure removes a newly
installed drop-in and reloads again; incomplete rollback is Action Required.
The application service depends only on narrow ports. Decky exposes only its
read-only preview, explicit approval, and token-consuming preparation methods;
none can request a Gamescope restart or presentation transition.

A packaged but inactive Gamescope shim provides the first presentation
mechanism boundary. It reads one strict, bounded, boot-scoped config from a
fixed state root, removes inherited eGPU render selection, and applies an
external connector/GPU only when the exact connector and vendor/device remain
uniquely present in the same boot. Stale, malformed, missing, or ambiguous
evidence selects a unique internal panel when available and otherwise preserves
the existing output arguments while clearing the eGPU selector. The companion
config store writes atomically from an exact transition binding. Neither the
shim nor its config store installs a systemd override, restarts Gamescope, or is
constructed by Decky.

The SteamOS signal adapter is a narrow Linux leaf mechanism: it maps only typed
graceful/force actions to `SIGTERM`/`SIGKILL`, opens a pidfd, verifies the
approved process start time, uses no shell or subprocess, has no numeric-PID
fallback, and returns categorical results. `main.py` constructs it only behind
the guarded service, root-owned journal, exact backend approvals, and mandatory
rescans. Missing pidfd capability blocks the preview before consent.

The Decky-wired `GuardedProcessReleaseService` composes redacted inspection,
explicit token issuance, fresh-sample execution, single-operation locking,
durable journaling, and no-repeat recovery. Graceful-attempt evidence remains a
private application value behind a bounded, expiring opaque receipt, so the
Decky facade cannot expose PID-plus-start-time-derived identities. Issuing a
force approval consumes that receipt; force is always a second confirmation.

The canonical sleep reducer is pure policy over exact eGPU presence/identity,
profile capabilities, game/save state, disconnect evidence, placement, and a
bounded original-request deadline. A delivery-independent coordinator now
normalizes Steam-menu/physical-button sources, binds the request to an exact
generation and eGPU/profile capability identity, persists every stage boundary,
requires fresh verification samples, and performs no directive itself. It
cannot show Safe to disconnect from
software-client readiness alone and cannot continue the original sleep request
before verified Portable recovery. Process release now participates as a child
of the same authoritative journal in simulation through strict substep events
and a backend-injected parent ID. Exact game close has the same child-step
boundary: one exact AppID/scope identity, explicit bounded consent, fresh
identity revalidation, durable pre-mechanism state, bounded Idle verification,
and fail-closed terminalization. The read-only scope adapter and application
service are implemented and simulated, but no production close mechanism or
Decky sleep delivery is wired. See
[Canonical sleep workflow](SLEEP_WORKFLOW.md).

Verified save is another strict child of that same parent. A backend-owned
recipe must match the exact game plus bound host/eGPU profiles, and a separate
proof observation must change to Verified after the attempt. The single-use
authority, durable pre-mechanism substep, bounded proof loop, close gate, and
privacy/capacity tests are implemented and simulated. No production recipe,
proof adapter, save mechanism, or Decky route exists. See
[Verified game-save child](GAME_SAVE.md).

The dormant canonical-sleep delivery facade keeps request identity and snapshot
generation backend-owned. It accepts only typed Steam-menu/physical-button
intent, re-observes through the coordinator, and binds consent/cancel to the
opaque active operation. Its payload mapper exposes only categorical flow
state, directives, durability, and the operation ID needed for exact consent or
acknowledgement. It is not constructed by Decky and has no directive mechanism.

Asynchronous cable-loss policy can request Portable recovery but can never
continue sleep. Even when the observed workflow is SleepPendingDisconnect, only
the canonical reducer may continue the exact unexpired request after separate
removal and Portable verification. Unknown pre-event placement fails closed;
after a verified loss invalidates the composite placement, every individual
recovery-critical identity and state must still be known before an attempt.

A dormant application-level unexpected-undock coordinator now binds one raw
eGPU/display-loss event to an exact semantic generation and independent sample,
re-observes exact loss and internal recovery readiness, makes one injected
Portable recovery attempt, verifies a fresh Portable result, and returns a
bounded identity-free trace. Primary failure invokes one separately bounded
Portable-preservation fallback; unknown/stale evidence or failed verification
enters Action Required. A sleep-pending event also requires the exact canonical
operation identity, but the coordinator has no sleep port and can only request a
later canonical re-check. It is not constructed by Decky and has no production
mechanism adapter. See
[Unexpected-undock recovery coordinator](UNEXPECTED_UNDOCK_RECOVERY.md).

The manual planner supports only the bounded Portable↔Docked-eGPU path and
verified no-ops. A mutating plan requires exact runtime host/eGPU profile
resolution, an ephemeral binding to every participating GPU/display, idle game
state, target readiness, and a verified source-placement rollback path.
Verified capability is accepted normally. One explicitly confirmed,
two-minute, single-use backend permit can authorize an exact Experimental plan
without promoting that capability. Docked-iGPU, Boosted Handheld, unknown, and
degraded sources are not silently coerced into this path. See
[Guarded experimental transitions](EXPERIMENTAL_TRANSITIONS.md).

An unwired supervised facade now joins the planner, experimental approval
store, durable orchestrator, and journal lifecycle. Read-only preview can model
one exact Portable↔Docked-eGPU request without issuing consent. Explicit
confirmation issues a maximum-two-minute single-use permit; execution consumes
it, requires the same semantic generation and ready integration, reconstructs
the exact plan, and delegates to the orchestrator. An incomplete journal blocks
new approval until recovery; a terminal journal blocks until its exact random
operation ID is acknowledged. No Decky RPC constructs this facade yet.

That same durable path now treats exact idle Docked-iGPU as a supported source
for a Docked-eGPU target. Boot config represents Docked-iGPU explicitly as TV
output plus the exact internal render GPU, and recovery can restore it. The path
remains experimental, approval-gated, and unwired; it does not watch for game
exit or initiate promotion automatically.

Controller and audio handoff also have pure decision policies only. External
controller promotion is independent from built-in suppression; suppression is
never planned without verified external input and a verified built-in recovery
path. Controller loss/undock restores and promotes built-in input first.
When promotion is verified but suppression is not, HDM keeps the built-in
controller active instead of failing the entire dock handoff.
External power-off may fall back to an independently verified disconnect
capability but is never assumed. Audio selection requires a verified usable
rollback output; otherwise the current usable output is preserved or Action
Required is reported. No input/audio observation or mechanism adapter is wired.

Exact Steam scope identity can now be enriched by a dormant read-only cgroup
and procfs adapter. It binds PID plus start time, captures private parent and
executable-basename evidence, and classifies native versus Proton only from
allowlisted environment-key presence. Incomplete or changing evidence discards
the entire process graph and returns a categorical Unknown result. No process
identity is public or journaled, and no Decky route or game mechanism uses this
adapter. See [Active game runtime evidence](GAME_RUNTIME.md).

One dormant read-only application service can bracket an exact eGPU-client
snapshot between two unchanged game-runtime samples and report categorical G1
render-node ownership. PID/start time, exact profile/eGPU identity, complete
scan, and game classification must all agree. This evidence explicitly does not
prove active rendering or authorize a placement transition.

A stronger dormant read-only path samples bounded DRM `fdinfo` engine counters
twice for an exact backend-resolved GPU binding. It requires stable game
processes, exact render node and PCI identity, unchanged DRM client/engine sets,
and monotonic counters. Only an observed counter increase proves activity on
that GPU for the sample window. The private G1 binding resolver independently
re-runs exact DRM/PCI/USB4 matching and accepts one character-device render node
under the exact GPU PCI device. It remains unwired; the evidence cannot
authorize a transition or certify a game by itself.

Compatibility Test Mode has one dormant application consumer for this evidence.
It requires a same-AppID internal-GPU baseline plus active G1 counters in a
Docked-eGPU snapshot, then records only a hashed generation and categorical
result. Existing explicit finish/review and simulation-promotion prohibitions
remain authoritative; no catalog update is automatic.

## Application layer

Application services coordinate ports and domain policy. The snapshot,
support-report, approval, replay, and guarded transition services share the
same authoritative observations and journal vocabulary. Manual and automatic
delivery still need one request facade before production wiring.

## Ports and adapters

Ports are narrow protocols defined by the application. The first SteamOS
adapters observe:

- DRM cards, connectors, modes, and EDID through sysfs
- PCI and USB4 topology
- Gamescope PID, arguments, active output, and render device
- Steam user-systemd game scopes
- exact certified-eGPU DRM/audio resource holders and mounted/swap storage
- bounded kernel link-health evidence

Kernel link-health collection remains pending. The implemented snapshot adapter
cross-correlates the other sources and emits blockers when any required source is
missing, conflicting, or ambiguous. Process classification is pure domain
policy; procfs and sysfs enumeration remain read-only SteamOS adapters.

Hardware profiles classify observations and quirks. They do not select devices
by enumeration order. The runtime registry selects a known profile only from
the exact current snapshot; ambiguity receives unknown capabilities.

Host recognition uses reviewed, normalized full DMI tuples rather than vendor,
product, or board-name substring similarity. G1 recognition requires the full
DRM/PCI/USB4 topology, expected bound drivers, one privacy-preserving USB4
identity, and an exact backend-only binding between the external GPU and its
disconnect scan. A profile-like name or matching GPU PCI ID cannot resolve a
runtime profile.

Profiles will expose conservative capabilities for eGPU transport, presentation,
audio, controller handoff, sleep behavior, and removal. A capability must be
supported by mechanism and evidence; unknown hardware receives no mutation
capability. Host and eGPU capabilities compose instead of forking the core.
The read-only diagnostic contract serializes these axes independently with a
typed value, confidence, and categorical evidence basis. It does not expose the
stable eGPU identity used for backend revalidation.

## Privilege boundary

Read-only discovery uses the least privilege that can verify each source. The
CLI runs unprivileged and reports protected Gamescope environment state as
unknown. The Decky adapter runs as root so it can read that environment, then
reads the Gamescope owner's user cgroups directly. A strict user-systemd command
allowlist remains only as a fallback. The dormant mutation runner independently
resolves the single verified Gamescope process owner's passwd record and live
user bus without username, UID, environment, or home-directory fallbacks. It
accepts only unit verification, daemon-reload, and a non-blocking restart of the
fixed `gamescope-session.target`; it uses absolute executables, a sanitized
environment, no shell, bounded output, and categorical errors. Decky constructs
it only for preparation, where the service can call daemon-reload and fixed-unit
verification but never the restart operation. Public RPCs are limited to
`get_snapshot`, the preview/token-approved support-bundle flow, the
preview/approval/token-consuming supervised preparation flow, and guarded
process inspect/approve/execute/acknowledge. No RPC accepts a command, system
path, device identity, PID, signal, or process target.

The first 0.2 safety mechanism is a backend-owned, parent-death-guarded
`systemd-inhibit` process. Exact G1 presence acquires its login1 lease, verified
absence or plugin unload terminates it, and backend process death terminates the
holder chain. Warning suppression is frontend-only and cannot affect the lease.

Future transition mutation is exposed through a small, typed API with no arbitrary command
or path inputs. The Decky entrypoint remains an adapter; it is not the domain or
transition engine.

Presentation activation will use a separately reviewed reversible user-service
integration. HDM will not patch SteamOS's `/usr/lib/steamos/gamescope-session`
script. The fixed integration store now installs or removes only HDM's exact
`90-handheld-dock-mode.conf`, refuses symlinks, unsafe ownership, modified
managed content, unknown environment files, and any competing `PATH` directive,
and retains the state directory on deactivation. File activation remains
separate from daemon-reload and restart. Existing eGPUBridge `PATH` ownership is
therefore reported as a conflict instead of being overwritten or chained. No
plugin path constructs the store yet.

Snapshot discovery records privacy-safe stage durations and the Decky frontend
uses an adaptive non-overlapping refresh loop: one second while discovering or
ready, 750 ms while identity/display evidence is settling, and three seconds in
a verified TV Docked state. The current certified live snapshot path measured 25–31 ms over
five end-to-end Decky RPC calls, so parallelizing sysfs/procfs sources is not
currently justified; snapshot consistency remains more important than shaving
that bounded observation time.

The Decky payload strips hardware stable IDs, connector/vendor identity,
Gamescope PID/output selectors, eGPU identity, and process PID/instance IDs.
Exact values remain in backend observations for revalidation and never cross
the frontend RPC boundary.

Support bundle construction, redaction, event rotation, size enforcement, and
one-time preview approval are application policy. The only file mechanism is a
fixed-boundary Decky delivery helper that creates the exact reviewed bytes in
the Decky user's Downloads directory. See [Privacy-safe support bundle](SUPPORT_BUNDLE.md).

## Transition design gate

Milestone 0.2 must add a durable transaction journal containing:

- request and trigger
- pre-transition snapshot
- desired state
- validated plan and blockers
- completed step and deadlines
- verification evidence
- rollback outcome

The engine re-observes safety-critical state immediately before applying a plan
to limit time-of-check/time-of-use races.

The sleep guard is not a display transition and does not use the transaction
journal. Its complete acquire/hold/release lifecycle and failure behavior are
defined in [ADR: G1 sleep guard](ADR_SLEEP_GUARD.md). The proposed frontend
layer that stops Steam before its preparation sequence is defined separately in
[ADR: Steam sleep preflight](ADR_STEAM_SLEEP_PREFLIGHT.md); it complements and
never replaces the backend login1 lease.

## Verification strategy

- Pure unit tests for mode and policy matrices
- Captured fixtures for discovery parsers
- Contract tests for Decky/backend payloads
- Failure injection for unavailable commands, stale identity, restart timeouts,
  partial configuration, and rollback failure
- Redacted supervised hardware captures for profile certification
