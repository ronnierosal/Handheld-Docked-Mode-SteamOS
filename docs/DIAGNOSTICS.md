# Read-only diagnostics

## Purpose

Milestone 0.1 exposes one privacy-safe JSON snapshot. It observes current state
and derives a mode; it does not write configuration, restart services, control a
display, or select a GPU.

From a source checkout on SteamOS:

```text
PYTHONPATH=backend python -m hdm.cli
PYTHONPATH=backend python -m hdm.cli --compact
```

After package installation, the equivalent command is `hdm-diagnose`.

Delivery adapters call `DiagnosticsApi.get_snapshot()` to receive the same
versioned dictionary without parsing CLI output. The Decky plugin is a thin
root-privileged wrapper around this API and exposes only `get_snapshot`.

Build the Decky package from a source checkout with:

```text
pnpm install --frozen-lockfile
pnpm typecheck
pnpm build
python scripts/check_plugin_package.py .
python scripts/build_plugin.py
```

The distributable archive is written under `out/`. Its Quick Access view shows
the inferred mode, running-game state, render GPU role, active display kind,
hardware support tier, and blockers. Refresh is its only action.

## Evidence sources

- `/sys/class/dmi/id`: host profile
- `/sys/class/drm`: GPU, connector, mode, and hashed EDID observations
- `/sys/bus/pci/devices`: PCI identity and topology
- `/sys/bus/thunderbolt/devices`: authorization and hashed USB4 identity
- `/proc/<pid>/cmdline`: unique Steam Gamescope session and output arguments
- `/proc/<pid>/environ`: Mesa Vulkan selector cross-check
- `/sys/fs/cgroup/user.slice`: running Steam game scopes for the observed
  Gamescope owner
- `systemctl --user list-units`: fallback scope inventory when the user cgroup
  hierarchy is unavailable

The primary game detector reads the Gamescope owner's current cgroup hierarchy,
which avoids crossing from Decky's root service into a user D-Bus session. The
only subprocess fallback allowed is the exact read-only systemd scope inventory.
It runs without a shell. The root fallback uses a fixed `runuser`/`env` prefix
whose username and UID are derived from the Gamescope process owner. All
alternate commands and mutation-shaped arguments are rejected by the command
boundary.

## Interpretation

`confidence` is explicit:

- `verified`: required sources agree
- `observed`: data exists but does not meet a certification rule
- `unknown`: a required source is missing, unreadable, conflicting, or ambiguous

`blockers` explain why a later transition would be unsafe. A successful
diagnostic command can still report an Unknown or Degraded mode; command success
means the report was produced, not that the machine is safe to mutate.

HDM verifies Portable only when the unique Steam Gamescope process, its
environment, one boot VGA GPU, and one active internal connector agree. It
verifies TV Docked only when the exact certified G1 topology, Gamescope GPU
selectors, and one connected external connector agree.

On the validated Ally X SteamOS build, the normal `deck` user cannot read the
Gamescope process environment even though it owns the process. An unprivileged
source-checkout run will therefore report `gamescope_environment_unreadable` and
leave render GPU and mode unknown. This is expected; do not weaken the rule.
The root Decky adapter exists specifically to make that protected environment
observable without changing the snapshot or inference policy.

## Privacy boundary

Normal JSON output excludes command lines, DMI strings, PCI bus addresses, raw
EDID, raw USB4 unique IDs, usernames, hostnames, home paths, IP addresses, and
systemd stderr. EDID and USB4 identities are represented by bounded hashes only.

Raw hardware evidence belongs in supervised, redacted test captures and is not
part of this default payload.
