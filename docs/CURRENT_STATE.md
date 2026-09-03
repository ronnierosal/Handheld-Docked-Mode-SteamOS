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
| Audited implementation baseline | `80bd8d4cfd6665387e806a548cfa040d508a5bd9` |
| Governance integration | Repository-governance commits follow that baseline locally; inspect `git log` for the live tip |
| Worktree | Clean at the audit baseline; verify live before acting |
| Remote relation | Mutable; run the commands above before relying on it |
| Project version | `0.2.0` from `package.json` |

Do not describe a public CI run, release, or remote branch as hardware
validation. Before integration, fetch, re-check ancestry and worktree state,
run the appropriate verification gate, and obtain explicit authorization before
push or publication.

## Build and deployment truth

- A Decky archive embeds semantic version and full source revision in
  `build_info.json`; dirty source reports `uncommitted`.
- Controlled artifacts bind the archive to `source-revision.txt` and a SHA-256
  manifest. ZIP filenames alone are never provenance.
- No artifact is promoted as current by this page. Build and verify one package
  from the intended clean commit for each validation session.
- The last live observation reports installed HDM `0.2.0`, public revision
  `0d66127cd0c2`, on 2026-09-02. With the G1 disconnected at installation and
  automatic TV docking enabled, a watched attach resolved the exact Ally X/G1
  profile, one EDID-ready TV, observed-Up link, and Idle game state. HDM restarted
  Gamescope, activated only the TV, and selected the RX 7600M XT for rendering.
  The player visibly confirmed Steam on the TV, and the durable presentation
  journal committed successfully. This is the first hardware-validated automatic
  TV/render transition for this candidate.
- Audio did not follow that successful transition because the installed build had
  no live PipeWire handoff. Read-only inspection found the exact G1 HDMI device and
  its SteamOS loopback sink while the internal loopback remained default. A single
  supervised `wpctl set-default` using a freshly resolved numeric node ID moved
  audio to the TV, and the player confirmed TV sound. The current worktree turns
  that proof into a guarded child of the presentation transition: it captures the
  current portable sink before attach, resolves the ephemeral G1 loopback node from
  the freshly verified G1 audio PCI function, changes and verifies the default,
  and restores the captured sink on transition rollback or Portable return. This
  code is committed and locally tested but not installed or hardware-validated.
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
- Automatic TV/display and render-GPU docking is hardware validated for one watched
  attach on installed `0d66127cd0c2`. The guarded automatic audio child is locally
  implemented and simulated; only its direct supervised G1 HDMI selection has
  hardware proof. Automatic selection and Portable restoration still require a
  watched install/connect/return cycle.
- Automatic docking remains behind an off-by-default persistent player opt-in.
  Boosted Handheld and physical
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

1. Shut down before disconnecting the attached G1, then install only while the G1
   is absent. Keep the Ally Portable long enough for HDM to capture its current
   default audio sink.
2. Repeat one watched automatic attach and verify TV picture, RX 7600M XT render
   selection, automatic TV audio, and one committed transition.
3. Exercise the supervised return-to-Portable path while the G1 remains attached;
   verify internal display and the exact captured portable audio before shutdown.
4. Design the Phase 2 unified installed diagnostic report and deployment record.
5. Resolve the P0/P1 hardware-coupling findings with narrow profile-driven seams
   and synthetic tests before claiming future-device extensibility.
