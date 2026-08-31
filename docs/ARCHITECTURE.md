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
composition, and a strict bounded transaction-journal schema. Its fixed-path
store and runtime orchestrator remain unconstructed by Decky, so no production
transition endpoint is enabled yet.

The guarded-process backlog has an internal approval service that issues
single-use tokens for backend-discovered eligible instances and requires a fresh
exact revalidation before returning internal signal targets. Graceful and force
approvals are distinct, and force requires prior graceful-attempt evidence. The
service is not exposed through Decky and no process-signal adapter exists.

A deterministic process-release runner now exercises a typed fake signal port.
It re-scans after every action, revalidates the remaining approved subset before
every next action, enforces per-signal deadlines, and exports an identity-free
audit. Clearing software clients never sets hardware-removal authority. See
[Guarded eGPU process-release contract](PROCESS_RELEASE.md).

Each simulated release operation owns a generated operation ID and records its
request, fresh observation, approval validation, plan, per-target fake steps,
re-scans, and terminal result in the shared transition journal. Tokens and
process/hardware identity never enter the exported journal.

The journal's dormant fixed-path file adapter enforces atomic append-only
progress for one operation, no-follow/exclusive temporary creation, byte bounds,
file and directory synchronization, and matching-terminal-only cleanup. It is
not constructed by Decky. See [Durable transition journal](TRANSITION_JOURNAL.md).

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

The dormant presentation mechanism now composes fresh binding/profile
revalidation, exact Gamescope-user revalidation, reversible integration status,
daemon-reload, fixed-unit verification, atomic target configuration, and a
non-blocking fixed-target restart. It rechecks the user before and after staging
the config. A synchronous restart failure restores the currently observed
source config immediately; a rollback-write failure is reported separately.
The orchestrator skips a redundant recovery restart when a fresh observation
already proves the source placement. Neither component is constructed by Decky.

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

The SteamOS signal adapter is a dormant leaf mechanism: it maps only typed
graceful/force actions to POSIX `SIGTERM`/`SIGKILL`, uses no shell or subprocess,
and returns categorical results. It is not constructed by `main.py`; delivery
contract tests forbid process-release wiring and RPC terms.

The canonical sleep reducer is pure policy over exact eGPU presence/identity,
profile capabilities, game/save state, disconnect evidence, placement, and a
bounded original-request deadline. It cannot show Safe to disconnect from
software-client readiness alone and cannot continue the original sleep request
before verified Portable recovery. See [Canonical sleep workflow](SLEEP_WORKFLOW.md).

Asynchronous cable-loss policy can request Portable recovery but can never
continue sleep. Even when the observed workflow is SleepPendingDisconnect, only
the canonical reducer may continue the exact unexpired request after separate
removal and Portable verification. Unknown placement fails closed.

The manual planner supports only the bounded Portable↔Docked-eGPU path and
verified no-ops. A mutating plan requires exact runtime host/eGPU profile
resolution, an ephemeral binding to every participating GPU/display, idle game
state, target readiness, and a verified source-placement rollback path.
Verified capability is accepted normally. One explicitly confirmed,
two-minute, single-use backend permit can authorize an exact Experimental plan
without promoting that capability. Docked-iGPU, Boosted Handheld, unknown, and
degraded sources are not silently coerced into this path. See
[Guarded experimental transitions](EXPERIMENTAL_TRANSITIONS.md).

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

Profiles will expose conservative capabilities for eGPU transport, presentation,
audio, controller handoff, sleep behavior, and removal. A capability must be
supported by mechanism and evidence; unknown hardware receives no mutation
capability. Host and eGPU capabilities compose instead of forking the core.

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
environment, no shell, bounded output, and categorical errors. No plugin code
constructs it. Public RPCs are limited to `get_snapshot` and the
preview/token-approved support-bundle flow. No RPC accepts a command, system
path, device identity, or process target.

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
