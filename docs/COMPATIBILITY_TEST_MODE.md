# Compatibility Test Mode

Compatibility Test Mode is currently a pure session policy and simulator. It
does not dock, undock, close a game, save, relaunch, signal a process, request
sleep, or publish a catalog result.

## Session flow

1. Require explicit player confirmation and select at least one test dimension.
2. Enable temporary diagnostics for the bounded session.
3. Capture a baseline generation, placement, game state, optional Steam AppID,
   and observed rendering GPU.
4. Record each requested result only from a fresh observation generation.
5. Require external-render evidence for a Verified eGPU result and internal
   render evidence for an iGPU-fallback result.
6. Disable temporary diagnostics before presenting results for review.
7. Require explicit human review to create evidence.

The session expires after at most two hours. Expiry, cancellation, stale
evidence, mismatched render evidence, or out-of-order events disable temporary
diagnostics and stop the session.

## Publication boundary

Reviewed simulation produces simulation evidence, which the catalog promotion
gate rejects. A future supervised hardware session may produce hardware-test
evidence, but the result still does not publish or promote itself; a separate
intentional catalog action must consume it. Telemetry never becomes Verified
automatically.

The evidence kind is backend-owned. Hardware-test evidence additionally
requires explicit trusted-runner authorization that must never be exposed as a
frontend boolean or general RPC argument. Immutable stage validation rejects a
reviewable record without its baseline, fresh generation history, and every
requested result.

Reviewed evidence is bound to the session's backend-owned catalog game identity
and the exact baseline Steam AppID, preventing a result from being reused for a
different title.

No runtime adapter, Decky RPC, UI, or catalog persistence is enabled.
