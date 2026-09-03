# Unexpected-undock recovery coordinator

## Status and boundary

R5 has a dormant application coordinator and deterministic simulator coverage.
It has no SteamOS mechanism adapter, Decky construction, RPC, topology watcher,
or hardware evidence. It cannot restart Gamescope, change display/GPU state, or
continue a sleep request in the installed product.

The coordinator handles only raw `egpu_removed` and `external_display_lost`
events. It consumes a backend-owned, freshness-tagged trigger observation and
uses injected observation, clock/wait, and recovery-mechanism ports. Exact
hardware identities remain ephemeral mechanism inputs and never enter the
bounded result trace.

This dormant action coordinator is distinct from the production
`NativePortableRecoverySupervisor`. The latter has no display mechanism: it
binds an exact idle TV-Docked baseline, observes the degraded Gamescope-down
interval seen during the 2026-09-02 Ally X/GPD G1 test, waits for SteamOS to
restart on the internal panel, and verifies Portable. Only after that verified
native result may it restore the previously captured Portable audio sink.

## Guarded sequence

```text
DETECT → VALIDATE → ATTEMPT → VERIFY → COMMIT
                         │
                         └─ failure → bounded Portable-preservation fallback
                                      → VERIFY or Action Required
```

- **Detect:** the first observation must exactly match the event generation and
  independent sample ID supplied by the backend event source.
- **Validate:** the pre-event placement must be known, the host/G1 and internal
  GPU/panel identities must be exact, Gamescope must be healthy, the game must
  be verified idle, and a newer semantic generation plus fresh sample must
  independently prove the bound eGPU/display loss.
- **Attempt:** one typed mechanism call receives only the backend-derived exact
  binding and current private snapshot.
- **Verify:** a bounded poll accepts only a fresh snapshot that independently
  proves Portable, retains the loss evidence, and matches the bound internal
  recovery path.
- **Commit:** the coordinator returns an identity-free terminal trace. This is
  an application result, not a durable production transition commit.

If the primary attempt fails, throws, or cannot verify in time, the coordinator
invokes one separate bounded fallback intended to undo partial work and retain
the Portable path. That fallback also must verify Portable. Failure or unknown
evidence enters Action Required; no unverified placement is accepted as usable.

The expected post-loss composite placement can be Unknown because its formerly
active renderer or display vanished. That does not promote unknown evidence:
the pre-event placement must be exact, and loss, host, game, Gamescope, internal
GPU, and internal panel evidence must each be independently known before the
mechanism is called.

Duplicate removal while already Portable is a verified no-op: a different
sample must still prove Portable stability. Concurrent requests fail closed.

## Canonical sleep separation

An unsolicited event and a `SleepPendingDisconnect` event have distinct result
origins. Sleep-pending recovery requires the exact canonical operation identity,
but the raw event coordinator never reads, advances, or writes the canonical
sleep journal and exposes no sleep mechanism. Its `authorizes_sleep` result is
always false.

After successful Portable recovery, a sleep-pending result only reports that
the canonical coordinator must re-check its own bound request, deadline,
removal evidence, fresh Portable sample, and journal order. Expired, cancelled,
unexpected, or out-of-order transactions remain awake.

## Production and hardware gates

Before any production wiring:

- route event recovery through the same serialized request facade and durable
  transition authority used by manual and sleep work
- provide a reviewed SteamOS observation/event adapter that binds exact semantic
  generation and sample IDs without trusting frontend identity
- provide reviewed primary and Portable-preservation mechanisms with bounded
  deadlines, rollback evidence, and startup recovery
- extend observation and verification for audio and controller recovery before
  claiming complete R5 behavior
- keep Decky construction and controls disabled until the relevant D0-D5 gates
  pass

Physical unexpected-unplug testing is D6. The current Ally X/GPD G1 profile is
not eligible: live removal is unsupported and shutdown-before-disconnect remains
mandatory. A future eligible profile requires explicit live-removal capability,
player presence, a written recovery path, redacted before/live/after evidence,
clean kernel evidence, and immediate stop on display, control, network,
Gamescope, PCIe/AER, USB4, or rollback failure.
