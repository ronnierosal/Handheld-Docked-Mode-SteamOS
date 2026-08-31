# HDM 0.1 read-only hardware validation — 2026-08-31

## Scope

The in-progress HDM 0.1 diagnostics CLI was copied to a unique `/tmp` directory
and run as the normal `deck` user on the reference ASUS ROG Ally X. The test made
no configuration changes, performed no service restart, and did not alter display
or GPU state.

Observed state:

- SteamOS Gamescope session active on `-O *,eDP-1`
- Internal `eDP-1` panel connected and uniquely inferred as active
- Internal AMD GPU `1002:15bf` present
- No external DRM GPU present
- Ally X DMI profile recognized as certified
- A Steam game scope detected, producing `game_state=running`

## Result

Host, DRM, output, and game-scope discovery passed on real hardware. HDM did not
claim Portable mode because the render GPU could not be verified at the CLI's
privilege level.

Although Gamescope runs as `deck`, this SteamOS build exposes
`/proc/<gamescope-pid>/environ` as root-owned mode `0400`. The normal user cannot
read it. The user systemd manager had no visible `MESA_VK_DEVICE_SELECT` value,
but manager state alone does not prove the already-running process environment.
The CLI therefore reported:

- Gamescope confidence: `observed`
- Inferred mode: `unknown`
- Blocker: `gamescope_environment_unreadable`
- Blocker: `render_gpu_unknown`

This is the intended fail-closed result.

## Delivery follow-up

The Decky delivery adapter was implemented around the unchanged
snapshot service. Its manifest requests Decky's root execution flag, and its
only public RPC is the read-only `get_snapshot` operation. When root observes the
Gamescope owner, the game-scope adapter reads that owner's current cgroups and
retains one strictly validated user-systemd query as a fallback. The root
Portable validation is recorded below; TV Docked remains pending.

## Decky root validation

The corrected 0.1 development package was installed through Decky Loader 3.2.6
under the separate `HandheldDockMode` directory. Decky ran `main.py` as root and
left the installed eGPUBridge directories unchanged.

The first root snapshot verified the protected Gamescope environment and
Portable mode, but the root-to-user systemd fallback returned a nonzero status
for the Steam game-scope query. HDM was changed to read the observed Gamescope
owner's cgroup hierarchy first, retaining the strict systemd query only as a
fallback. After reinstall, the live Decky RPC reported:

- mode: `portable`
- game state: `idle`
- support tier: `certified`
- render GPU: `internal-gpu`
- output order: `*,eDP-1`
- blockers: none

The Quick Access Decky page listed **Handheld Dock Mode** beside eGPUBridge, CSS
Loader, and SteamGridDB. This validates the native plugin lifecycle, root
snapshot boundary, frontend registration, and Portable read-only path. TV
Docked validation remains pending until the G1 and TV are naturally connected;
HDM performed no transition or hardware mutation during this check.

## Live G1 disconnect-readiness validation

The schema 2 package was then deployed through Decky's authenticated installer.
With the G1 naturally attached while Gamescope remained in Portable mode, the
first scan failed closed because the captured topology contains several Intel
`8086:15ef` bridge functions plus an identity-less authorized USB4 host-router
record. The original profile had incorrectly required one `15ef` function in
the full GPU ancestry and counted the host-router record as an external device.

The profile was corrected to require one top-level removable `15ef` bridge,
allow downstream PCI bridge functions, and ignore only the identity-less USB4
host-router node. Any additional or unidentified external authorized USB4 node
still blocks certification. Unit fixtures now cover the observed multi-bridge
topology and host-router record.

After reinstall, the live root RPC reported:

- exact G1 identity: verified (raw USB4 identity omitted)
- host/G1 support tier: `certified`
- mode: `portable`; Gamescope remained on the internal GPU and panel
- game state: `idle`
- disconnect scan: complete
- storage routed through the G1: none observed
- exact resource client: `wireplumber`, holding G1 `audio_control`
- client classification: protected SteamOS session process, not close-eligible
- disconnect readiness: blocked

The native Quick Access panel rendered the same blocker and the explicit
read-only notice. No process was signaled, no GPU/display selector changed, and
no disconnect or hardware removal was attempted. TV Docked transition
validation remains pending.

## Live G1 sleep-guard validation

The schema 3 package was installed through the same Decky-native flow while the
G1 remained naturally attached. Decky's temporary dynamic-loader environment
initially prevented the system `systemd-inhibit` binary from starting; the
bounded process adapter was corrected to remove only loader and Python path
overrides before launching the SteamOS system binaries.

After reinstall, three independent observations agreed:

- the root Decky RPC reported `sleep_guard.required=true`,
  `sleep_guard.active=true`, and `confidence=verified`
- `systemd-inhibit --list` showed **Handheld Dock Mode** holding a `sleep` lock
  in `block` mode as root
- the Quick Access panel showed **Sleep protection** and **Blocked while G1
  attached**, with the frontend-only **Never show this explanation again**
  control

The system remained in Portable mode, no game was running, and `wireplumber`
remained the protected audio client blocking disconnect readiness. No sleep
request, process signal, GPU/display change, disconnect, or physical removal was
attempted. Quick Access, physical-button, idle, and direct login1 sleep-request
tests remain separate supervised acceptance work.
