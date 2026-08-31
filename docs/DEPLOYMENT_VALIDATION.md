# Deployment and validation strategy

This strategy is designed for remote development without turning SSH into a
production feature or allowing an automated test to strand the handheld.

## Non-negotiable deployment rules

- Deploy one combined artifact built from one clean commit. Never layer frontend
  and backend files from different branches or commits.
- Record the source commit and SHA-256 of the package and installed critical
  files before interpreting device behavior.
- Install through Decky Loader's native lifecycle. Do not replace files under a
  running plugin and call that a valid deployment.
- Boot/recovery validation starts with the G1 disconnected. Attach it only at a
  named supervised stage.
- Remote automation stops before suspend, reboot, Gamescope restart, display or
  controller mutation, USB4 reset, physical disconnect, or anything likely to
  remove SSH/network/presentation.
- A clean Quick Access panel proves UI health only. It does not prove safe GPU
  teardown, display recovery, or removal readiness.
- Preserve a known-good package and use graceful Steam/Decky recovery before
  considering a hard power cycle.

## Artifact build and provenance

From a clean checkout at the intended commit:

```text
python scripts/check_architecture.py
python -m unittest discover -s tests -v
python -m compileall -q backend tests scripts
pnpm test:frontend
pnpm typecheck
pnpm build
python scripts/check_plugin_package.py .
python scripts/build_plugin.py
git status --short
git rev-parse HEAD
Get-FileHash -Algorithm SHA256 out/*.zip
```

Do not deploy if the worktree contains unexplained generated or source changes,
any check fails, or package contents do not match the source commit.

For each candidate, retain a small local manifest containing only:

- HDM version and source commit
- package SHA-256
- build timestamp
- test/check results
- intended validation stage
- rollback package SHA-256

Do not place device secrets or raw hardware identifiers in that manifest.

## Validation ladder

Each stage must pass before proceeding. A failure returns to diagnosis; it does
not authorize retrying later stages with speculative fixes.

### D0 — Local deterministic checks

Run the complete build/check matrix. For transition work, also run snapshot
replay, fake-clock, timeout, rollback, and failure-injection scenarios.

Permitted: local files and simulators.  
Prohibited: device mutation.

### D1 — Package inspection

Verify manifest, root flag, bundled backend/frontend versions, public RPC
allowlist, archive paths, and package hash. Compare the complete artifact with
the rollback candidate.

### D2 — Device baseline, G1 disconnected

With the player available for the initial install:

1. Confirm Ally display, controls, network, Steam, Decky, and SSH are healthy.
2. Confirm the G1 is physically disconnected.
3. Capture a redacted read-only snapshot and boot/session identifiers.
4. Reinstall through Decky's native action.
5. Verify backend/frontend hashes, one plugin instance, expected RPC schema,
   and no unexpected inhibitor.
6. Exercise unload/reload and confirm leases/resources return to baseline.

This stage may be observed remotely after the physical precondition is confirmed.

### D3 — Read-only G1 attachment

Only after the player naturally connects the G1 and confirms visible control:

1. Capture before/live snapshots.
2. Verify exact profile identity, TV/EDID state, Gamescope, render GPU, game
   state, disconnect blockers, and both sleep-protection layers.
3. Verify adaptive polling and support preview without saving or changing state.
4. Keep the G1 attached; do not test removal.

Automated SSH work remains read-only. Any unknown identity or game state stops
the stage.

### D4 — Supervised UI and non-destructive lifecycle

Use one exact written action at a time with the player watching the Ally and a
known recovery path ready. Examples include the pending blocked-Sleep warning
proof and support-bundle preview/save proof.

For a blocked-Sleep warning test, success requires all of:

- warning remains visibly actionable until acknowledged
- Steam logs the request as blocked before preparation
- boot ID is unchanged and uptime is continuous
- login1 never enters PreparingForSleep
- Gamescope and the internal display remain usable
- backend and Steam preflight leases remain active

Enforcement without a visible warning is a failed UX acceptance result, not a
pass.

### D5 — Supervised bounded mutation

Allowed only after the relevant ADR, pure policy, simulator, rollback, approval,
and adapter tests pass. Start with disposable user-process fixtures; then move
to idle transitions. Capture redacted before/live/after evidence.

No automated suspend, reboot, live disconnect, USB4 reset, or destructive
display/session action is permitted at this stage.

### D6 — Physical and access-risk experiments

Create a separate experiment plan with explicit player presence, acceptance
criteria, stop conditions, and recovery. This stage covers physical power-button
behavior, actual suspend, Gamescope restart, controller suppression, unexpected
unplug, and eGPU teardown/removal.

The current Ally X/G1 profile may not enter a live-removal experiment merely
because software clients are gone. AMDGPU teardown safety is an independent
hardware gate.

## Remote-safe harness

The read-only `capture` family is implemented in
[Remote read-only validation](REMOTE_VALIDATION.md). It streams a fixed Python
collector over SSH stdin, writes no remote file, and saves one bounded redacted
JSON result locally. The future harness may provide two command families:

- `capture`: read-only snapshot, bounded health checks, package provenance, and
  redacted log/result retrieval.
- `run-replay`: local-on-device deterministic fixtures that do not touch live
  system mechanisms.

It must not expose arbitrary commands, paths, PIDs, signals, or shell fragments.
Payload transport should be structured or base64-safe to avoid host-shell
quoting changes. Every operation needs a deadline and machine-readable result.

Production HDM must not listen for remote development commands. SSH remains the
maintainer's external development boundary.

## Stop conditions

Stop all mutations and preserve evidence if any of these occurs:

- display becomes black, frozen, or unexpectedly rerouted
- SSH/network becomes unstable
- Gamescope, Steam, or Decky restarts unexpectedly
- sleep-preparation state changes unexpectedly
- G1 identity/topology changes or becomes unknown
- kernel logs show GPU reset, PCIe/AER recovery, USB4 teardown, or
  `amdgpu_device_fini_hw` stalls
- plugin/frontend/backend provenance cannot be proven identical
- rollback cannot be verified

Do not stack fixes on the live device. Return to the last safe stage, repair one
cause in source, rebuild one complete artifact, and repeat from D0.

## Immediate deployment queue

1. With the player present, complete only the corrected persistent warning
   proof on the already installed commit.
2. Complete controller-visible support preview/save acceptance separately.
3. Implement the R1 control-plane and simulator locally.
4. Deploy R1 first with the G1 disconnected, then perform read-only attachment
   checks. R1 must not add a mutation RPC.
