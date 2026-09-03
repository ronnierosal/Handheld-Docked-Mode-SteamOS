# Current state

**Audience:** players, testers, maintainers, and contributors<br>
**Evidence reviewed:** 2026-09-02<br>
**Maturity:** development build; no general public release

This is a readable snapshot, not the mutable engineering record. Verify the
repository [current-state document](https://github.com/ronnierosal/Handheld-Docked-Mode-SteamOS/blob/main/docs/CURRENT_STATE.md)
before building, installing, testing, or making a support claim.

## What exists today

- Read-only host, eGPU, DRM, Gamescope, game, link, and readiness discovery
- Exact matching for the first Ally X plus GPD G1 profile
- Privacy-safe diagnostics and support preview/export
- Sleep protection foundations and guarded process-release workflows
- Deterministic transition and rollback behavior exercised through tests and fakes
- An exact-profile automatic TV Docked path behind an off-by-default persistent
  player opt-in

Implementation and simulation do not prove that a physical transition succeeds.

## Latest supervised hardware result

The installed build observed on 2026-09-02 successfully detected the authorized
USB4 path, exact Ally X/G1 profile, RX 7600M XT, G1 audio, an EDID-ready TV,
link health, and an idle game state. Automatic docking restarted Gamescope. The
handheld panel went dark and the TV detected a signal, but the TV stayed black.
HDM timed out and verified recovery to Portable.

The investigation found two distinct launch-binding defects:

1. the config writer and Gamescope launch shim derived different boot bindings;
2. after that was corrected, the root-owned config was written with permissions
   that prevented the Gamescope user from reading it.

Both have narrow code fixes. The readability fix still requires a new clean
build, controlled installation, and supervised Ally X + GPD G1 + TV test before
the TV transition can be described as hardware working.

## Capability status

| Capability | Status |
|---|---|
| Exact first-profile detection | Implemented and observed on hardware |
| Read-only diagnostics | Implemented; privacy-safe public projection |
| Automatic TV Docked transition | Implemented; successful TV image not yet hardware proven after latest fix |
| Failure rollback to Portable | Observed during the latest supervised attempt |
| Boosted Handheld | Not available; hardware behavior unproven |
| Physical live G1 removal | Unsupported |
| Other handheld/eGPU profiles | Not certified by inference |

The current GPD G1 rule is still: restore or retain a safe state, shut down, and
only then physically disconnect it.
