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

## Application layer

Application services coordinate ports and domain policy. Milestone 0.1 has a
snapshot service only. Later, one transition service will accept both manual and
automatic requests.

## Ports and adapters

Ports are narrow protocols defined by the application. The first SteamOS
adapters observe:

- DRM cards, connectors, modes, and EDID through sysfs
- PCI and USB4 topology
- Gamescope PID, arguments, active output, and render device
- Steam user-systemd game scopes
- bounded kernel link-health evidence

Kernel link-health collection remains pending. The implemented snapshot adapter
cross-correlates the other sources and emits blockers when any required source is
missing, conflicting, or ambiguous.

Hardware profiles classify observations and quirks. They do not select devices
by enumeration order.

## Privilege boundary

Read-only discovery uses the least privilege that can verify each source. The
CLI runs unprivileged and reports protected Gamescope environment state as
unknown. The Decky adapter runs as root so it can read that environment, then
queries the Gamescope owner's user systemd bus through a strict command
allowlist. Its only public RPC is `get_snapshot`.

Future mutation is exposed through a small, typed API with no arbitrary command
or path inputs. The Decky entrypoint remains an adapter; it is not the domain or
transition engine.

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

## Verification strategy

- Pure unit tests for mode and policy matrices
- Captured fixtures for discovery parsers
- Contract tests for Decky/backend payloads
- Failure injection for unavailable commands, stale identity, restart timeouts,
  partial configuration, and rollback failure
- Redacted supervised hardware captures for profile certification
