# Canonical sleep workflow policy

The canonical sleep reducer models one original player request without calling
Steam, login1, game processes, display mechanisms, or eGPU mechanisms. It is a
simulation/policy foundation, not an enabled sleep workflow.

## Entry policy

- Verified eGPU absence retains normal sleep.
- A profile explicitly verified sleep-safe may retain normal sleep.
- Unknown presence, identity, game state, or required evidence keeps the device
  awake and enters Action Required.
- A running game requires explicit close consent. Unverified/manual save
  capability adds a mandatory progress-loss warning.
- A verified triggerable autosave directive is emitted only after consent and
  only from the capability bound when the request began.
- Consent denial cancels the original sleep request and keeps the device awake.

## Client and removal policy

After verified game exit, the reducer requires a complete disconnect scan:

- a game that starts during release invalidates the transition
- storage, game, protected, system, or unknown clients enter Action Required
- eligible ordinary user clients route to the separate preview/approval process
  release workflow
- clearing software clients is not removal readiness

`Safe to disconnect` requires all of:

- an exact eGPU profile with `live_removal_verified`
- a complete client/storage scan with no blockers
- an independent verified render/display removal-readiness result

The current GPD G1 profile has `shutdown_before_disconnect`; it routes to a
shutdown-first instruction and never emits `Safe to disconnect`. The original
sleep request is cancelled on that branch.

## Original-request continuation

For a future live-removal-verified profile, verified physical removal moves the
workflow to portable recovery while the handheld remains awake. The original
sleep request is emitted exactly once only after Portable placement is verified.
Out-of-order events or failed recovery enter Action Required.

Each request has a bounded deadline (15 minutes by default, one hour maximum).
At or after expiry, HDM cancels the request and keeps the device awake instead
of suspending from stale consent or stale hardware evidence.

## Current boundary

The reducer and game-save capability vocabulary are pure and unit tested. There
is no game-close adapter, save adapter, sleep-continuation adapter, power-button
integration, or Decky workflow RPC. Current login1 and Steam preflight behavior
remains governed by the existing sleep ADRs.
