# ADR: G1 sleep guard

## Decision

HDM 0.2 owns a login1 `sleep` inhibitor in `block` mode whenever the supported
Ally X observes a G1 candidate. SteamOS's exact `systemd-inhibit` command owns
the returned descriptor. HDM launches it only through an internal helper that
arms Linux parent-death signals before execution; the command's held no-op child
uses the same guard.

This follows login1's native lifetime rule: the inhibitor exists only while the
returned descriptor remains open. See the official
[login1 manager API](https://www.freedesktop.org/wiki/Software/systemd/logind/)
and [systemd-inhibit behavior](https://www.freedesktop.org/software/systemd/man/latest/systemd-inhibit.html).

## Lifecycle

| Observation | Action |
|---|---|
| G1 candidate present, including incomplete identity | Acquire or retain the lease. |
| G1 verified absent on the supported host | Release the lease. |
| Host, DRM, or identity evidence unknown | Hold the current lease state. |
| Plugin unload | Release the lease. |
| Backend crash | Parent-death signals terminate the holder chain; the kernel closes the descriptor. |
| Acquisition failure | Report `sleep_guard_inactive`, retry, and show a critical warning. |

Acquisition and release are idempotent. The controller polls the small
host/DRM/PCI/USB4 evidence set rather than the full process-client snapshot.
The process boundary removes Decky's transient dynamic-loader and Python path
overrides before starting SteamOS's `/usr/bin/python` and
`/usr/bin/systemd-inhibit`; all other environment entries are preserved.

## User experience

Quick Access always shows the current protection state while the G1 is attached.
It also emits a game-aware Decky toast and explanatory panel. **Never show this
explanation again** stores a frontend-only preference. It cannot release the
lease, hide inactive-protection failures, or alter blockers.

## Boundaries

- The only public RPC remains `get_snapshot`.
- No sleep request is initiated by HDM.
- No power-menu interception is treated as the safety boundary.
- No display/GPU transition, process signal, or physical removal is added.
- Quick Access, physical power button, idle sleep, and direct login1 sleep paths
  require separate supervised hardware validation.
