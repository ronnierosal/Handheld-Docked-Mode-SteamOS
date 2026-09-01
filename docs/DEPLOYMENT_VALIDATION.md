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

A successful CI run may provide the same controlled candidate as a short-lived
workflow artifact. Before using one, compare its workflow commit with
`source-revision.txt`, verify its ZIP against `SHA256SUMS.txt`, and confirm the
installed QAM **HDM build** row after Decky's native install. CI artifacts are
not releases and must not be installed automatically.

## Validation ladder

Each stage must pass before proceeding. A failure returns to diagnosis; it does
not authorize retrying later stages with speculative fixes.

### D0 — Local deterministic checks

Run the complete build/check matrix. For transition work, also run snapshot
replay, fake-clock, timeout, rollback, failure-injection, and unexpected-loss
Portable recovery scenarios. R5 checks must prove exact trigger/sample binding,
no raw-event sleep authority, bounded primary/fallback attempts, and fail-closed
unknown evidence.

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

### D2a — Read-only gameplay observation overhead

Run this only after D2 passes, with the G1 still disconnected and the player
watching the internal display. It validates the installed panel's game-aware
observation behavior; it is not an eGPU, sleep, or performance certification.

1. Record the installed package commit and SHA-256, then confirm the Quick
   Access **HDM build** row shows the expected short revision before starting
   one ordinary Steam game on the internal display. `uncommitted` or
   `unavailable` is not sufficient provenance for this stage.
2. Open Quick Access → Handheld Dock Mode. Confirm the panel is controller
   usable and reports a running game without changing the display, audio,
   controller assignment, or game session.
3. Open Troubleshooting. Confirm it says that additional checks wait until HDM
   confirms no game is running. Do not invoke any destructive or export action.
4. Leave the panel open for at least fifteen seconds while playing normally,
   then close it and continue playing. The implementation's expected cadence is
   one essential read-only snapshot at most every five seconds while game state
   is running; this hardware check must not claim a performance measurement from
   subjective observation alone.
5. Record whether the panel stayed responsive and whether the player observed
   any display, input, audio, game-session, or obvious performance regression.

Pass only if the game and handheld remain usable with no unintended system
change. On any regression, close/unload HDM or reinstall the recorded rollback
package through Decky's native lifecycle; do not troubleshoot by restarting
Gamescope, suspending, rebooting, or changing GPU/display settings remotely.

### D3 — Read-only G1 attachment

Only after the player naturally connects the G1 and confirms visible control:

1. Capture before/live snapshots.
2. Verify exact profile identity, TV/EDID state, Gamescope, render GPU, game
   state, disconnect blockers, and both sleep-protection layers.
3. Verify adaptive polling and support preview without saving or changing state.
4. In troubleshooting details, verify the Docked-iGPU watcher status remains
   categorical and contains no AppID, scope, device identity, or generation.
   Do not treat `promotion_ready` as approval or proof of G1 rendering.
5. Keep the G1 attached; do not test removal.

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
- verbose diagnostics require a visible confirmation, show the selected bounded
  countdown, disable immediately, and return to off after the selected expiry
- support export remains a separate explicit preview/save action; enabling
  logging alone creates no file or upload

Enforcement without a visible warning is a failed UX acceptance result, not a
pass.

### D5 — Supervised bounded mutation

Allowed only after the relevant ADR, pure policy, simulator, rollback, approval,
and adapter tests pass. Start with disposable user-process fixtures; then move
to idle transitions. Capture redacted before/live/after evidence.

No automated suspend, reboot, live disconnect, USB4 reset, or destructive
display/session action is permitted at this stage.

For guarded process release, D5 starts only with a disposable same-session user
fixture intentionally holding one non-critical G1 resource. Do not use Steam,
Gamescope, Decky, a game, storage, or a real user application as the first
target:

1. Capture the exact candidate package hash and redacted baseline.
2. Verify the controller preview shows only the fixture name/resource category
   and reports all protected clients separately.
3. Cancel once and prove no signal occurred.
4. Approve graceful release once; verify durable `step_started` preceded the
   signal and a fresh scan observed the fixture exit or continued hold.
5. If testing force, use a fixture designed to ignore `SIGTERM`, acknowledge the
   graceful result, review the second destructive warning, and approve once.
6. Verify PID reuse/new client/storage/incomplete-scan injections all fail
   closed and that physical-removal authority remains false.
7. Confirm Steam, Gamescope, Decky, display, controls, network, and sleep guard
   remained healthy. Keep the G1 attached.

Any unexpected target, missing journal event, missing rescan, lost UI, or
uncertain result stops process testing and preserves the G1 connection.

For the presentation path, D5 begins with **preparation only** while the G1 is
disconnected, the system is verified Portable/idle, and the player is watching:

1. Preview the exact Gamescope user, integration fingerprint, conflicts, and
   rollback status.
2. Resolve any competing `PATH` owner explicitly. HDM must not overwrite an
   eGPUBridge drop-in.
3. Approve one short-lived preparation token.
4. Install the exact HDM drop-in, daemon-reload the exact user manager, and
   verify `gamescope-session.service` remains loaded.
5. Confirm no Gamescope restart occurred and display, controls, SSH, Steam, and
   Decky remain healthy.

Preparation is not a display-transition test and does not authorize one.

### D6 — Physical and access-risk experiments

Create a separate experiment plan with explicit player presence, acceptance
criteria, stop conditions, and recovery. This stage covers physical power-button
behavior, actual suspend, Gamescope restart, controller suppression, unexpected
unplug, and eGPU teardown/removal.

The current Ally X/G1 profile may not enter a live-removal experiment merely
because software clients are gone. AMDGPU teardown safety is an independent
hardware gate.

Unexpected-undock R5 hardware validation additionally requires production
event/mechanism wiring through the shared serialized transition authority,
exact pre-event and loss evidence, verified internal recovery readiness, bounded
Portable-preservation fallback, and independent audio/controller verification.
It may run only on a profile whose live-removal capability has already been
verified. The current GPD G1 is therefore ineligible; do not use it for an
unexpected-unplug test.

The first presentation experiment must start G1-disconnected and Portable. It
restarts Gamescope once through the shim with a Portable target, proves the
internal display/control/SSH recovery, and proves rollback before any G1/TV
target is attempted. The later G1/TV attempt requires the game to be idle,
stable exact G1 and EDID evidence, a fresh single-use Experimental permit, and
before/attempt/verified-or-rollback captures. A black display, lost input, lost
SSH, unexpected process restart, or unknown placement stops the stage.

## Remote-safe harness

The read-only `capture` family is implemented in
[Remote read-only validation](REMOTE_VALIDATION.md). It streams a fixed Python
collector over SSH stdin, writes no remote file, and saves one bounded redacted
JSON result locally. The future harness may provide two command families:

An explicit root read-only variant uses only the fixed
`sudo -n /usr/bin/python3 -` prefix, verifies that the payload actually ran at
the requested privilege, and stops if non-interactive sudo is unavailable. It
does not make the standalone collector an observer of Decky's inhibitor lease.

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

1. Build and provenance-record one clean candidate from the current transition
   foundation; do not deploy mixed artifacts.
2. With the player present and G1 disconnected, repeat D2 and the corrected
   persistent-warning proof.
3. Complete controller-visible support preview/save acceptance separately.
   On the next candidate, inspect the new identity-free `game_evidence` event
   while idle and while one game is running; idle must skip deep scans and the
   running result must never expose AppID, scope, PID, PCI, DRM-node, or
   generation data.
4. Inspect for the known eGPUBridge/HDM `PATH` conflict before any presentation
   preparation.
5. Review the Decky-native preparation preview/confirm flow on the built
   candidate; keep transition controls and attach automation disabled.
6. Run the disposable-process D5 validation as a separate supervised session;
   do not combine it with sleep, display, or physical-removal testing.
7. Run D5 preparation, then schedule the first D6 Portable-only shim restart
   with the player watching. Do not combine it with a G1/TV transition.
