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
| Audited implementation baseline | `8d96b9c398f77c26ebbef50b5fb1c7d402695169` |
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
- The last authoritative repository note reports installed HDM `0.2.0`, public
  revision `fd2d38f2fa04`, observed on 2026-09-01. A 2026-09-02 read-only SSH
  attempt could not reach the Ally, so the current installed build is
  **Unknown** until it is observed again.
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
- The corrected native TV transition still needs a fresh supervised
  Ally X + GPD G1 + TV proof.
- Automatic docking is implemented behind an off-by-default persistent player
  opt-in and remains hardware-validation-required. Boosted Handheld and physical
  live eGPU removal are not available. The current G1 policy remains shutdown
  before disconnect.

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

1. Return the full local verification matrix to green before a new candidate.
2. Re-observe the installed build and device state before deployment or hardware
   interpretation.
3. Complete the separately owned supervised TV-switch proof with one exact,
   provenance-recorded candidate.
4. Design the Phase 2 unified installed diagnostic report and deployment record.
5. Resolve the P0/P1 hardware-coupling findings with narrow profile-driven seams
   and synthetic tests before claiming future-device extensibility.
