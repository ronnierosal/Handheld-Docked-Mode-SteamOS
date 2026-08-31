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
