# Prepared docked idle eligibility

This pure contract compares two caller-supplied monotonic observations. It
starts only from fresh, consistent combined-handoff eligibility with an exactly
Idle game. A later observation must retain the same opaque attachment binding
and generation, provide a new sample, and remain fresh/consistent/eligible for
at least 5,000 ms.

Before that boundary it reports `not_yet_stable`; at or after the boundary it
reports `prepared` with opaque current evidence only. Reused samples never
mature. Running or Unknown game state, stale/inconsistent evidence, changed
attachment/generation, or an invalid monotonic order invalidates the window.

The contract owns no timer, poller, scheduler, persistence, action, permit,
Decky route, or Safe Undock authority. `prepared` is not a display/GPU/audio/
controller handoff and does not release any helper. A future unified transition
owner must independently re-observe, validate, and obtain required consent.
