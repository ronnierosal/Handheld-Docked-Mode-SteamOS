# Guarded experimental transitions

Hardware validation is a certification gate, not an implementation gate. HDM
may implement an Experimental mechanism before certification when the operation
is exact, observable, bounded, recoverable, and explicitly approved for a
supervised test.

## Runtime profile resolution

The runtime registry resolves capabilities from the complete current snapshot.
It selects the Ally X host profile only from the exact host profile ID and the
GPD G1 profile only when one verified external GPU has the stable identity that
the exact G1 matcher assigned and the complete combination remains Certified.
Unknown or ambiguous evidence receives the unknown profile and no mutation
right. Resolution does not change Experimental capabilities to Verified.

The manual planner derives an ephemeral transition binding containing the exact
host/eGPU profiles and current internal/external GPU and display stable IDs.
This binding is needed by a mechanism but is excluded from the privacy-safe
transition journal and support exports. A mutating plan cannot exist without a
complete binding.

## Experimental approval

Verified capabilities need no experimental exception. An Experimental display
handoff requires a separate backend-issued permit that is:

- based on explicit user confirmation
- valid for at most two minutes
- single use
- bound to the operation, observation generation, target placement, host
  profile, eGPU profile, and ephemeral eGPU identity

The planner rejects a missing, stale, or differently bound permit. This is not
a general `allow_experimental` frontend boolean. No public RPC or automatic
attach path can currently issue or consume the permit.

## Presentation shim boundary

The plugin package contains an inactive `bin/gamescope` shim and a fixed-path
boot-scoped config store. Packaging is not activation. No installer, systemd
override, Gamescope restart, public RPC, or automatic attach path currently
enables it.

For a docked selection, the shim requires the config's exact external connector
and GPU vendor/device pair to remain uniquely present in the current boot. It
never chooses a GPU by DRM card order or PCI address. Invalid or stale config
falls back to a unique connected internal panel when possible and always clears
an inherited HDM eGPU render selector. If a safe output cannot be selected, it
preserves the existing output arguments rather than guessing.

Future activation must be reversible, must refuse conflicts with another
user-service `PATH` override, and must remain a distinct supervised operation.
The orchestrator must still re-observe and verify the resulting placement; a
successful Gamescope exec is not transition success.

The fixed user-service command boundary is implemented but unwired. It derives
the target user only from the one verified Gamescope process owner and requires
the matching passwd home plus a live user bus. There is no `deck`, UID 1000, or
environment fallback. It can verify the fixed service, reload that user's unit
configuration, or queue a non-blocking restart of the fixed Gamescope target;
it cannot accept an executable, unit, path, command, or environment value from
an RPC.

The reversible drop-in store is also implemented and unwired. It owns exactly
`90-handheld-dock-mode.conf`, creates only fixed descendants of the verified
user home, and never edits Valve's session script. Activation rejects modified
HDM content, unsafe ownership/symlinks, unknown environment files, and any
other drop-in that can set, pass, or unset `PATH`. In particular, an installed
eGPUBridge path shim is a conflict to resolve explicitly during a supervised
test. Deactivation removes only the byte-exact HDM file and leaves its bounded
state directory for recovery evidence.

## Certification boundary

An approved Experimental plan authorizes one controlled attempt after the
runtime orchestrator and mechanism are available. It does not mark the result
Verified or Certified. Promotion still requires the intentional hardware
review rules in [Hardware support](HARDWARE_SUPPORT.md) and a captured
before/attempt/verification/rollback record.
