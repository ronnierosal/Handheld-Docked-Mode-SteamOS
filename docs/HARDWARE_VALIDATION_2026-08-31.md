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

The Decky delivery adapter has now been implemented locally around the unchanged
snapshot service. Its manifest requests Decky's root execution flag, and its
only public RPC is the read-only `get_snapshot` operation. When root observes the
Gamescope owner, the game-scope adapter queries that owner's user systemd bus
through one strictly validated command shape.

Live root validation remains pending. The next hardware check must install the
package beside eGPUBridge, verify Portable through the Decky process, and later
repeat the same read-only check in a naturally established TV Docked state. Mode
inference must not fall back to assuming that absence of `--prefer-vk-device`
means the iGPU is selected. No transition implementation is required for either
check.
