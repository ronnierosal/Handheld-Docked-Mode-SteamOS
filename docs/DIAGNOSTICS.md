# Read-only diagnostics

## Purpose

The plugin exposes one privacy-safe JSON snapshot. It observes current state and
derives a mode; it does not write configuration, restart services, control a
display, select a GPU, or signal a process. In 0.2 the Decky lifecycle also owns
the narrowly scoped login1 sleep-inhibitor lease.

From a source checkout on SteamOS:

```text
PYTHONPATH=backend python -m hdm.cli
PYTHONPATH=backend python -m hdm.cli --compact
```

After package installation, the equivalent command is `hdm-diagnose`.

Delivery adapters call `DiagnosticsApi.get_snapshot()` to receive the same
versioned dictionary without parsing CLI output. The Decky plugin is a thin
root-privileged wrapper around this API. Its explicit public allowlist also
covers support preview/export, reversible presentation preparation, guarded
process release, and categorical Docked-iGPU watcher status/acknowledgement.
Transition approval or execution is not public.

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
hardware support tier, blockers, sleep-protection state, and read-only eGPU
disconnect readiness. It also shows progressive connection readiness and the
total snapshot duration. Refresh and warning-preference controls do not change
system state or release the inhibitor. Support export writes only after an exact
redacted preview and one-time approval.

An optional controller-friendly troubleshooting section is off by default. It
derives categorical state, confidence, blocker codes, client categories,
resource types, and stage timings from the existing snapshot. It does not issue
hardware mutation and does not render stable hardware IDs, connector names,
vendor IDs, or process IDs. It also shows the categorical Docked-iGPU watcher
stage. If that read-only watcher enters Action Required, the only offered action
acknowledges and cancels its private watch so observation can resume; it cannot
approve or execute promotion. Closing/reopening the plugin hides the section
again.

## Evidence sources

- `/sys/class/dmi/id`: host profile
- `/sys/class/drm`: GPU, connector, mode, and hashed EDID observations
- `/sys/bus/pci/devices`: PCI identity and topology
- `/sys/bus/thunderbolt/devices`: authorization and hashed USB4 identity
- `/proc/<pid>/cmdline`: unique Steam Gamescope session and output arguments
- `/proc/<pid>/environ`: Mesa Vulkan selector cross-check
- `/proc/<pid>/fd`, `comm`, `stat`, and `cgroup`: exact certified-eGPU DRM and
  audio resource holders, bounded process names, process-instance fingerprints,
  and Steam-game ownership
- `/sys/class/block`, `/proc/self/mountinfo`, and `/proc/swaps`: storage routed
  through the certified G1 topology and whether it is mounted or swap-backed
- `/sys/fs/cgroup/user.slice`: running Steam game scopes for the observed
  Gamescope owner and an exact AppID only when recognized scope names agree
- `systemctl --user list-units`: fallback scope inventory when the user cgroup
  hierarchy is unavailable

The primary game detector reads the Gamescope owner's current cgroup hierarchy,
which avoids crossing from Decky's root service into a user D-Bus session. The
only subprocess fallback allowed is the exact read-only systemd scope inventory.
It runs without a shell. The root fallback uses a fixed `runuser`/`env` prefix
whose username and UID are derived from the Gamescope process owner. All
alternate commands and mutation-shaped arguments are rejected by the command
boundary.

Scope-derived AppID identity is currently retained only inside the read-only
game scan. Multiple/future scope formats leave it unknown, and it is not present
in the public schema or support bundle.

The production Docked-iGPU observer resolves the exact Gamescope user and binds
each watch to a hash of the Gamescope PID, Linux start time, and UID. A missing
or changed process generation fails closed. It attempts to arm only from exact
running Docked-iGPU evidence. Its serialized lifecycle uses a fifteen-second
ineligible cadence and five-second active cadence. Watch-only promotion-ready
is visible for one active interval and then cleared; Action Required quiesces
until acknowledgement. A supervisor retries transient startup or runner failure
after thirty seconds. The public
status contains only stage, reason code, bounded next-poll timing, and boolean
inspection/acknowledgement flags. Watch ID, AppID, scopes, profile identities,
eGPU identity, and observation generations remain private. The production
composition has no supervised-preview port, so `inspection_available` remains
false and no transition authority can be created.

## Interpretation

`confidence` is explicit:

- `verified`: required sources agree
- `observed`: data exists but does not meet a certification rule
- `unknown`: a required source is missing, unreadable, conflicting, or ambiguous

`blockers` explain why a later transition would be unsafe. A successful
diagnostic command can still report an Unknown or Degraded mode; command success
means the report was produced, not that the machine is safe to mutate.

Snapshot schema 2 adds `disconnect_readiness`. Schema 3 adds `sleep_guard`,
including whether the guard is required, active, and verified. A disconnected eGPU is not an
error and reports `applicable: false`. With an exact certified G1 present, the
scan fails closed unless both card and render nodes, every visible process FD,
and attached-storage usage can be inspected. Any exact resource holder or
mounted/swap storage makes `ready` false. This is evidence only: HDM does not
signal a process or remove hardware.

The report also has a top-level diagnostics schema `2`. It retains schema 1's
allowlisted stage names and millisecond durations for DRM, Gamescope, game
state, PCI, USB4, host, eGPU identity, disconnect clients, and total snapshot
collection. Timings carry no paths, device addresses, connector names, process
identifiers, or command output. Schema `2` adds the versioned
`hardware_profiles` record. It reports exact/absent/unknown host and eGPU profile
resolution plus independent typed capability rows for transport, display,
audio, controller, power-button, sleep, and removal behavior. Each row contains
only an axis, categorical value, confidence, and evidence basis. Delivery schema
`2` carries this record to Decky without exposing DMI strings, PCI/DRM names,
USB4 hashes, EDIDs, or stable device identities. Unknown or incomplete profile
sets keep composed handoff capabilities Unknown.

The CLI never acquires an inhibitor. The root Decky backend polls only the host,
DRM, PCI, and USB4 identity needed for the sleep lease. Candidate G1 presence
acquires a login1 `sleep`/`block` inhibitor; verified absence and plugin unload
release it. Unknown observations hold the current state. The exact
`systemd-inhibit` holder and its no-op child both carry Linux parent-death
signals, so plugin failure tears down the holder chain and releases the lock.

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

The Decky JSON output excludes command lines, DMI strings, PCI bus addresses,
raw or hashed hardware identity, connector names, vendor/device IDs, usernames,
hostnames, home paths, IP addresses, systemd stderr, PIDs, and process-instance
IDs. eGPU clients expose only a bounded `comm` name and categorical kind,
resource types, eligibility, and reason. Exact identities remain backend-only
for revalidation and never cross the Decky RPC boundary. Raw process start
times may exist only in the private backend snapshot used to defeat PID reuse;
they are stripped from Decky delivery and support export together with
cgroup paths, file-descriptor targets, and device paths.

Raw hardware evidence belongs in supervised, redacted test captures and is not
part of this default payload.

Support Preview performs one additional bounded game/GPU evidence pass only
when the user invokes that existing action. Idle or unknown game state skips
deep process and DRM inspection. For one exact running Steam game, HDM brackets
private runtime identity and samples the independently resolved internal and G1
render nodes within one shared snapshot/runtime window. Either target being
Unknown marks the comparison incomplete. The support event contains only categorical game exactness,
runtime type, client/activity states and counts, reason codes, and placement.
AppID, scopes, PIDs, process start times, executable data, PCI addresses, DRM
nodes, stable IDs, and evidence generations never enter the preview. Failure of
this optional pass records a categorical unavailable event and does not prevent
the base support preview.

## Temporary verbose logging policy

Normal bounded HDM events remain available for support bundles. Additional
verbose events are off by default and require explicit player confirmation.
The only allowed durations are 30 minutes, one hour, two hours (the default
selection), and until reboot. There is no permanent option.

The policy uses a monotonic deadline, returns automatically to normal logging at
expiry, sanitizes details before in-memory retention, and retains the existing
rotating event cap. Consent is held only in memory, so a plugin/service restart
disables verbose logging. An until-reboot
session also checks the current boot identity on every status/event operation;
a changed or unreadable identity disables the session fail closed. Boot identity
is used only for equality and is never exported.

This controller is implemented and unit tested but is not wired to Decky RPC or
the UI. No durable consent, arbitrary system log collection, or upload exists.
