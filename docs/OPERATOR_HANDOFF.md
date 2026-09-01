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

The staged candidate, installed version, and local checkout may change. Confirm
each independently before relying on this snapshot.

## Continuity status

- North Star: HDM is a safety-first SteamOS handheld reliability companion, not
  only a dock-mode controller. It must prevent or soften player-visible PC
  paper cuts, explain state clearly, and use only validated, reversible recovery
  authority. Docking/eGPU work remains the initial, tightly gated domain.
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
