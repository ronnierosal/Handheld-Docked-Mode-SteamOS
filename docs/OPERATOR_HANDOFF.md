# Maintainer and agent handoff

This note gives a fresh Codex chat the current, operator-safe starting point.
It is an operational snapshot, not proof of a certified hardware behavior.
Always re-check live state before making a hardware claim.

## Repository and current snapshot

- Repository: `C:\Users\SLDD\Codex Projects\Handheld-Docked-Mode-SteamOS`
- Branch: `main`
- Local source status must be checked with `git rev-parse HEAD` and `git status --short`.
- Latest locally verified application slices at this handoff: `36da94f` (optional
  authoritative health observations) and `c271309` (their measured timing).
  They are local-only, not installed-device evidence, and may be unpushed.
- Last verified installed HDM build on the Ally: `0.2.0`, revision `e73d249`
- Last verified loader state: `plugin_loader.service` active.
- A signed candidate based on `3584a4d` is staged but was not installed when
  this note was written.
- **Current local candidate (2026-09-01):**
  [candidate `84219fc`](DEPLOYMENT_CANDIDATE_2026-09-01.md) passed D0/D1
  locally and has an inspected combined archive. It is not yet D2-stageable:
  no local rollback archive matches the last observed installed `e73d249`
  baseline. Do not install until that artifact or an explicit rollback plan is
  available.

The staged candidate, installed version, and local checkout may change. Confirm
each independently before relying on this snapshot.

## Checkpoint and worker-integration policy

The ordered bounded queue and required check-in template are in
[Worker queue](WORK_QUEUE.md). It enables continuation only when a worker is
triggered; it is not an autonomous scheduler.

For every meaningful verified checkpoint, update the appropriate tracked
continuity, product, or roadmap note with the current goal, completed change,
exact verification, evidence status (**Implemented**, **Simulated**, or
**Hardware Validated**), blocker, and next safe task. Keep this concise and
exclude secrets, raw device identities, and transient logs.

Commit only small coherent verified slices. Before integrating completed worker
work, inspect its diff and relevant tests, confirm clean ancestry and no
unrelated changes, then fast-forward or make the smallest safe merge promptly.
Resolve conflicts deliberately. Record the integration and verification here;
do not leave a growing queue of completed worktree commits unintegrated.

## Continuity status

- North Star: HDM is a safety-first SteamOS handheld reliability companion, not
  only a dock-mode controller. It must prevent or soften player-visible PC
  paper cuts, explain state clearly, and use only validated, reversible recovery
  authority. Docking/eGPU work remains the initial, tightly gated domain.
- The [Ally ↔ G1 end-to-end journey](WORK_QUEUE.md#1-ally--g1-end-to-end-dock-play-sleep-and-undock-journey)
  is the current player-facing parent focus. Its stages remain independently
  gated; it does not authorize live GPU migration, unattended disruption, or a
  safe-unplug claim without fresh complete evidence.
- **Repository-health audit (2026-09-01):** `main` is clean and passed
  architecture, compile, 659 Python tests (5 skipped), 47 frontend tests,
  typecheck, build, package, and diff checks. The completed read-only-profile
  and unexpected-undock worker commits are patch-equivalent to `46e69dd` and
  `77e518f` already on main; no duplicate merge was made. The canonical-sleep
  replay worktree predates later guarded-save/journal work and must not be
  merged. The offline-readiness draft was reviewed, committed on its worker
  branch, and cleanly cherry-picked as `7db80d9`; main verification then passed.
  No hardware status changed.
- The optional workflow/peripheral health inputs are deliberately not constructed
  by the production snapshot path yet. A future owner must be authoritative and
  event-driven or measured/cached; do not add continuous peripheral scans to
  normal Quick Access refreshes.
- The latest unattended read-only capture observed the supported handheld/G1
  profile, an idle game, a usable internal display, and an inactive external
  display. Render-GPU identity remained unavailable at unprivileged privilege;
  safe undock was not ready because the client scan was incomplete and protected
  session clients remained. Standalone capture cannot observe the Decky sleep
  lease. These are observations, not transition or sleep validation.
- A fresh unprivileged, no-write capture on 2026-09-01 again observed the exact
  supported profile, idle game, one active internal panel, and one connected
  inactive external display. Render selection remained Unknown; the client scan
  was incomplete with protected session clients, so Safe Undock was not ready.
  Snapshot collection took about 25 ms. The installed 0.2.0 capture lacks the
  current link-health schema and its fixed-file provenance does not match this
  checkout. Unchanged wake aggregates remain capability observation only, not
  suspend or wake-cause proof.
- Root read-only capture currently requires a maintainer-installed noninteractive
  rule. Its absence is a diagnostic limitation, not a reason to broaden sudo.
- The two saved wake-diagnostic aggregates were unchanged. That does not identify
  a wake source or establish suspend safety.
- The local Quick Access redesign keeps the first screen to Mode, Health,
  Connection, and Game. Safety/actions remain compact and troubleshooting is
  opt-in. Returning from long troubleshooting details resets the QAM panel
  scroll and focuses the first native in-panel control, so controller focus
  does not fall through to QAM Back. The redesign is locally tested only.
- Next concrete work: review the locally built Quick Access package with the
  maintainer; before any install, obtain a maintainer-approved exact deployment
  plan with the G1 disconnected and player-visible recovery available.
- Physical power-button double-press Safe Undock is infeasible at the current
  boundary: HDM cannot observe first/second press edges without risking ordinary
  Steam Sleep behavior. Keep the button Steam-owned; the specified future
  fallback is verified **Guide + Y** hold routed to the ordinary `UNDOCK`
  request. See [physical power-button feasibility](POWER_BUTTON_SAFE_UNDOCK.md).
- Power and Link Health currently exposes only existing exact-bridge PCIe link
  state plus optional current GT/s/lane metrics in Troubleshooting. Link-change
  notices are non-blocking: one Down/Unknown instability episode and one later
  Up observation are shown, while flapping is suppressed. Power, battery, thermal, throttle,
  budget, and sustained-churn inference remain unimplemented/Unknown. No health
  display enables a transition or Safe Undock. See [Power and Link Health](POWER_LINK_HEALTH.md).
- **Stage 1.1 checkpoint (local-only):** attach readiness now withholds
  `ready_idle` unless the exact bridge reports an observed Up link; a Down or
  unavailable link is delivered as a categorical waiting state. This is neither
  TV activity nor render-GPU, bandwidth, controller/audio, or Safe Undock proof.
  It adds no event source, RPC, polling loop, deployment, or transition authority.
- **Stage 1.2 checkpoint (pure local contract):** a direct player Dock request
  during an exactly running game can be retained only with an opaque attach
  binding and bounded expiry. Cancellation, expiry, changed binding, or Unknown
  game evidence terminalize it; a fresh idle result yields only a non-authorizing
  eligibility handoff. No persistence, scheduler, Decky route, game-close action,
  or display/GPU/audio/controller transition is wired.
- **Stage 1.3 checkpoint (pure eligibility/rollback contract):** combined
  handoff can be eligible only from one fresh opaque-bound observation with
  verified Idle game, active external display/render/audio/controller, and
  verified Portable display/audio/built-in-controller rollback facts. Missing,
  stale, contradictory, inactive, or game-active facts fail closed; a partial
  future attempt is rollback-required. No mechanism, plan, permit, RPC, or
  hardware proof is added.
- **Stage 1.4 checkpoint (pure revalidation contract):** caller-supplied
  combined-eligible Idle observations can yield prepared evidence only after a
  new same-attachment/same-generation sample at least five seconds later.
  Activity, uncertainty, stale/inconsistent facts, binding/generation changes,
  or reused samples never mature. The contract has no timer, scheduler,
  persistence, action, permit, RPC, or Safe Undock authority.
- **Stage 1.5 checkpoint (pure read-only readiness):** exact attachment/topology,
  complete clear-client scan, Idle game, verified Portable display/render/audio/
  built-in-controller fallback, and inactive external display must share one
  fresh opaque observation before HDM can say only `ready_for_revalidation`.
  Protected/incomplete scans, activity, fallback gaps, contradictions, stale
  evidence, and binding changes fail closed. This never claims physical unplug
  safety and has no process/helper/device action or transition authority.
- **Stage 1.6 checkpoint (pure result presentation):** a human-facing result
  consumes only the Stage 1.5 revalidation-bound result. It can say only
  evidence-insufficient, not-ready, revalidate-required, or eligible to begin
  supervised physical validation. Missing acknowledgement or a changed/missing
  attachment binding, generation, or sample invalidates the presentation.
  Eligibility is not a safe-to-unplug claim and creates no action authority;
  rerun Stage 1.5 immediately before any later separately approved physical
  test.
- **Implemented (local-only contract):** interrupted docked-sleep recovery has
  a privacy-safe checkpoint projection over the existing canonical sleep
  journal plus a pure post-wake evidence classifier. It emits at most one
  controller-friendly notice per durable checkpoint in a UI process. “Handheld
  restored” requires exact G1 absence plus independently verified handheld
  display, input, and audio; game/session outcome is never inferred. There is
  no startup wiring, sleep listener, topology watcher, recovery mechanism, or
  Ally deployment. Current unattended captures cannot supply this proof.
- **Product policy, not implemented behavior:** after an interrupted docked
  sleep incident, HDM should verify usable handheld display/input/audio before
  considering the original game/session stopped. Only complete recovery
  evidence plus no known update, sync, or repeat-failure concern may permit a
  future default game relaunch. The first successful use must offer one
  non-intrusive choice to retain automatic restart or turn it off. No current
  code has wake wiring, those concerns, a relaunch adapter, or hardware proof;
  never claim a game crash or successful recovery from passive capture.
- **Implemented (pure local contract):** Offline Readiness classifies only
  supplied categorical install, download, entitlement, cloud-save, local
  blocker, and known online-check evidence as ready-to-try, attention needed,
  online check needed, or Unknown. It exposes no game/account/path/time data,
  never promises offline launch, and has no Steam collector, UI, persistence,
  or hardware evidence. A future source now requires a reviewed, local-only,
  identity-minimized, benchmarked, bounded-cost declaration before its fresh
  categorical evidence can be classified; game-active or unknown collection is
  deferred, and stale or unadmitted evidence remains Unknown. There is still no
  Steam collector, delivery integration, or collection authority. Next gate is
  a separately reviewed local Steam/launcher source design, including privacy
  handling, measured game-impact/freshness behavior, and explicit authority.

## SSH access

The development computer connects directly to the Ally; Codex is not installed
on the Ally.

```powershell
$key = Join-Path $env:USERPROFILE ".ssh\hdm_ally_deploy_v2"
ssh -i $key -o BatchMode=yes -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes deck@<current-ally-host>
```

Obtain the current host from the maintainer at capture time. If SSH fails, ask
again; do not scan the network or guess another account/key. The private key remains on the
development computer. Never copy it to the Ally, commit it, print it, or ask
for the maintainer's password.

Read-only deployment provenance check:

```powershell
ssh -i $key -o BatchMode=yes -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes deck@<current-ally-host> `
  'cat /home/deck/homebrew/plugins/HandheldDockMode/build_info.json; systemctl is-active plugin_loader.service'
```

Use `python scripts/remote_capture.py --host <current-ally-host> --identity-file $key`
for a redacted read-only capture. Read [Remote read-only validation](REMOTE_VALIDATION.md)
before using it.

## Direct deployment

The normal maintainer-operated path is:

```powershell
.\scripts\deploy_hdm_to_ally.ps1 `
  -HostName <current-ally-host> `
  -UserName deck `
  -IdentityFile $key `
  -ConfirmDeploy `
  -InteractiveSudo
```

It runs the complete local verification matrix, uploads a temporary archive,
creates a timestamped backup, atomically replaces only
`/home/deck/homebrew/plugins/HandheldDockMode`, restores the packaged shim mode,
and restarts only `plugin_loader.service`. It does not restart Gamescope or
invoke display, GPU, sleep, controller, audio, or eGPU actions. It prompts for
the maintainer's SteamOS sudo password at the final replacement step; Codex
must never request or handle that password.

An unattended signed updater is being enabled. Its fixed root-owned helper is
under `/var/lib/handheld-dock-mode/hdm-deploy-plugin` and accepts only a signed,
strictly validated HDM ZIP plus matching signature. It keeps a rollback backup
and restarts only `plugin_loader.service` after a successful replacement.

At this snapshot, the first sudoers rule used SteamOS argument globs that did
not match a valid invocation. A corrected installer is staged at:

```text
/home/deck/Downloads/install_ally_deploy_helper.sh
```

The maintainer must run the following once, interactively, before an agent may
use the signed updater without a password prompt:

```sh
sudo sh /home/deck/Downloads/install_ally_deploy_helper.sh
```

After the maintainer confirms success, verify the exact rule with `sudo -n -l`
and then invoke only the staged exact helper command. Do not broaden the
sudoers rule or add arbitrary shell authority.

## Safety and validation boundaries

- The GPD G1 and TV state must be re-observed; no current connection/display
  state should be inferred from this note.
- Deployment/restarting `plugin_loader.service` is distinct from a display or
  sleep test. It does not certify any hardware transition.
- Never run sleep, reboot, Gamescope restart, display handoff, USB4 reset,
  process signaling, or physical eGPU removal remotely without the current
  supervised-validation gate and maintainer visibility.
- The earlier watched TV-switch attempt failed closed on the internal panel;
  configuration-path repair exists in source but is not hardware-certified.
- The G1 sleep/immediate-wake issue remains unverified and must not be treated
  as fixed.

Read `AGENTS.md`, `docs/DEPLOYMENT_VALIDATION.md`, `docs/REMOTE_VALIDATION.md`,
and `docs/HARDWARE_VALIDATION_2026-08-31.md` before altering deployment or
hardware-facing behavior.

## Required local verification

Before handing off a change, run:

```text
python scripts/check_architecture.py
python -m unittest discover -s tests -v
python -m compileall -q backend tests scripts
pnpm typecheck
pnpm test:frontend
pnpm build
python scripts/check_plugin_package.py .
git diff --check
```
