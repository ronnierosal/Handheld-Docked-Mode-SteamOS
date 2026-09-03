# Current state

Last repository audit baseline: **2026-09-02**. This page records a dated
implementation baseline rather than attempting to name its own containing Git
commit. Re-verify all mutable facts before a build, deployment, merge, or
hardware session:

```text
git status --short --branch
git rev-parse HEAD
git rev-list --left-right --count origin/main...HEAD
```

## Repository

| Field | Audited value |
|---|---|
| Branch | `main` |
| Audited implementation baseline | `22e19446e904bfda8f78719f460cc96ae926bebc` plus the launch-config readability fix in this change |
| Governance integration | Repository-governance commits follow that baseline locally; inspect `git log` for the live tip |
| Worktree | Clean at the audit baseline; verify live before acting |
| Remote relation | Local `main` was 67 commits ahead of `origin/main` before the governance slice |
| Project version | `0.2.0` from `package.json` |

GitHub does not yet contain the audited local implementation. Do not describe a
public CI run, release, or remote branch as validating these 67 local commits.
Before integration, fetch, re-check ancestry and worktree state, run the
appropriate verification gate, and obtain explicit authorization before push or
publication.

## Build and deployment truth

- A Decky archive embeds semantic version and full source revision in
  `build_info.json`; dirty source reports `uncommitted`.
- Controlled artifacts bind the archive to `source-revision.txt` and a SHA-256
  manifest. ZIP filenames alone are never provenance.
- No artifact is promoted as current by this page. Build and verify one package
  from the intended clean commit for each validation session.
- The last live observation reports installed HDM `0.2.0`, public revision
  `7227e739300f`, on 2026-09-02. The owner-aware journal correction is installed,
  and its exact presentation acknowledgement cleared the prior terminal journal.
  A later watched attach progressed from the authorized USB4 bridge to the exact
  Ally X/G1 profile, RX 7600M XT, G1 audio function, one EDID-ready TV, observed-Up
  link, and Idle game state. Automatic docking restarted Gamescope, the handheld
  screen went dark, and the TV reported a signal but remained black. The launch
  shim fell back to the internal panel; verification timed out after 15 seconds
  and HDM verified recovery to Portable. Candidate `22e19446e904` corrected the
  boot-binding material, but a repeated watched attach produced the same safe
  fallback. Direct inspection then proved the root-owned writer had created the
  per-user launch config as mode `0600`, so the `deck`-owned Gamescope shim could
  not read it.
- Historical candidate and deployment records are snapshots, not current truth.
  See [Operator handoff](OPERATOR_HANDOFF.md) and dated deployment records for
  their exact context.

The repository-to-runtime proof chain is:

```text
repository HEAD
  -> clean build embeds version + full revision
  -> artifact manifest binds revision + ZIP SHA-256
  -> installer validates embedded metadata
  -> installed build_info reports version + revision
  -> runtime diagnostics reports that installed identity
```

Artifact checksum and deployment timestamp are not yet persisted in installed
runtime metadata. That is a Phase 2 provenance gap, not a fact to infer from a
local ZIP.

## Capability summary

- Read-only discovery, exact first-profile identity, diagnostics, health,
  support preview/export, sleep protection, and guarded/supervised foundations
  are implemented to the evidence levels recorded in [Roadmap](ROADMAP.md).
- Deterministic transition/recovery behavior does not by itself prove hardware
  operation.
- The native TV transition reached a real Gamescope restart but did not reach the
  TV. Live evidence exposed a boot-binding hash mismatch between the config writer
  and launch shim, followed by a root-writer/user-reader permission mismatch.
  The local correction preserves the raw boot identity only in memory for the
  private binding hash, retains the hashed boot identity in the serialized
  config, and writes that identity-free config root-owned/read-only to ordinary
  users (`0644`) so the Gamescope user can consume it. It needs a fresh
  supervised Ally X + GPD G1 + TV proof.
- Automatic docking is implemented behind an off-by-default persistent player
  opt-in and remains hardware-validation-required. Boosted Handheld and physical
  live eGPU removal are not available. The current G1 policy remains shutdown
  before disconnect.
- A prior live attach exposed a terminal shared journal that automatic docking
  mislabeled as a TV acknowledgement even though both the presentation and
  process-release services rejected ownership. The local correction reports
  the categorical owner, offers exact acknowledgement only for a terminal sleep
  journal, keeps unknown/incomplete journals fail-closed, and re-arms the same
  attachment after a valid owner acknowledgement. That correction is installed;
  the exact presentation acknowledgement and subsequent automatic retry were
  observed on hardware.

## Active ownership

- **Hardware-journey driver:** ASUS ROG Ally X + GPD G1 connect, TV Docked,
  gameplay, return to Portable, sleep/recovery, reconnect, and repetition on
  real hardware.
- **Repository-governance driver:** authority, documentation, Git/version truth,
  diagnostics contract, parity/UI audits, CI, templates, and repository hygiene.

The governance workstream must not deploy, run hardware transitions, or edit the
hardware driver's active runtime path without coordination. Shared documents
must preserve the distinction between implemented, simulated, installed, and
hardware-tested behavior.

## Immediate gates

1. Build the boot-binding correction from a clean commit and verify its embedded
   revision and checksum.
2. Shut down before disconnecting the attached G1, then install only while the G1
   is absent and re-observe the Portable baseline.
3. Repeat one watched automatic attach and complete the TV-switch proof with the
   exact provenance-recorded candidate.
4. Design the Phase 2 unified installed diagnostic report and deployment record.
5. Resolve the P0/P1 hardware-coupling findings with narrow profile-driven seams
   and synthetic tests before claiming future-device extensibility.
