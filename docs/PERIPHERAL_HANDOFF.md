# Controller and audio handoff foundation

HDM treats controller and audio handoff as child work of the authoritative
transition transaction. They are not a second mutation engine.

## Current implementation boundary

R7a implements a pure, delivery-independent planning foundation:

- schema-versioned controller/audio observations
- one semantic generation plus an independent per-scan sample ID
- independent complete and exact identity gates for controller and audio
- private opaque controller and audio-output bindings
- categorical blockers and privacy-safe public traces
- a composite ordered plan in which every step requires fresh verification

R7b adds a bounded read-only SteamOS sysfs inventory for gamepad-capable input
nodes and sound cards. It hashes node paths into private opaque bindings and
retains no names or paths. By default every controller identity remains
unmapped and audio's current default output remains unobserved, so the adapter
cannot authorize a handoff. Exact private hints may be supplied only after a
supervised mapping test; even then the adapter never claims input verification
or audio-output verification.

The adapter hashes the complete private inventory into a semantic generation
and issues a distinct sample ID on every collection. Timestamp-only collection
does not invalidate a plan, but any candidate, mapping, completeness, or
categorical-error change does.

There is no mechanism adapter, Decky RPC, or live handoff authority. The Ally X
and GPD G1 profile values remain Unknown or Experimental and authorize no
unsupervised controller/audio change.

## Ordering and recovery rules

Dock plans order eligible work as:

1. promote the exact external controller
2. select the exact external audio output
3. optionally suppress the built-in controller

Suppression is omitted unless external input, built-in input, and the exact
built-in restore path are verified. A future executor must observe and verify
each preceding step before advancing; a static plan is never proof that a
change succeeded.

Undock plans order eligible work as:

1. restore the exact built-in controller
2. promote it to primary input
3. restore the exact portable audio output
4. optionally disconnect or power off the external controller

External-controller power-off is used only when independently Verified. It may
fall back to disconnect only when that separate capability is Verified.

One subsystem may expose safe work while another has a non-destructive blocker.
Such a plan is `partial`, not fully `ready`. An incomplete or inexact subsystem
produces no steps for that subsystem. Stale shared evidence, a repeated sample,
or a changed semantic generation produces no steps at all.

## Privacy boundary

Bindings exist only in the private plan. The public trace contains schema,
status, direction, typed step codes, and blocker codes. It omits bindings,
generation, sample ID, device names, addresses, paths, account identity, and
audio node identity.

## Required follow-on

1. Extend the read-only inventory with supervised identity/default-output
   mapping evidence and fixture parsers for SteamOS variants.
2. Re-plan from the same semantic generation and a new sample immediately
   before each step.
3. Execute one typed step through the shared transition journal.
4. Observe and verify the exact target.
5. On failure, restore the exact rollback binding and verify recovery.
6. Add privacy-safe diagnostics before supervised hardware experiments.

Implementation and simulation do not verify controller ordering, built-in
suppression, Bluetooth disconnect/power-off, TV audio selection, or portable
audio recovery on physical hardware.
