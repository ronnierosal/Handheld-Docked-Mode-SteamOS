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
progress. The current code implements only the original placement inference and
transition vocabulary. The typed split, journal, and replay engine are the next
read-only control-plane milestone; see [Authoritative roadmap](ROADMAP.md).

The first control-plane slice now defines typed placement and workflow states,
request/plan/deadline/failure/recovery values, conservative host/eGPU capability
composition, and a strict bounded transaction-journal schema. The journal is an
immutable value with a persistence port only: no storage adapter or production
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

## Application layer

Application services coordinate ports and domain policy. Milestone 0.1 has a
snapshot service plus a bounded privacy-safe support-report service. Later, one
transition service will accept both manual and automatic requests.

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
by enumeration order.

Profiles will expose conservative capabilities for eGPU transport, presentation,
audio, controller handoff, sleep behavior, and removal. A capability must be
supported by mechanism and evidence; unknown hardware receives no mutation
capability. Host and eGPU capabilities compose instead of forking the core.

## Privilege boundary

Read-only discovery uses the least privilege that can verify each source. The
CLI runs unprivileged and reports protected Gamescope environment state as
unknown. The Decky adapter runs as root so it can read that environment, then
reads the Gamescope owner's user cgroups directly. A strict user-systemd command
allowlist remains only as a fallback. Public RPCs are limited to `get_snapshot`
and the preview/token-approved support-bundle flow. No RPC accepts a command,
system path, device identity, or process target.

The first 0.2 safety mechanism is a backend-owned, parent-death-guarded
`systemd-inhibit` process. Exact G1 presence acquires its login1 lease, verified
absence or plugin unload terminates it, and backend process death terminates the
holder chain. Warning suppression is frontend-only and cannot affect the lease.

Future transition mutation is exposed through a small, typed API with no arbitrary command
or path inputs. The Decky entrypoint remains an adapter; it is not the domain or
transition engine.

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
