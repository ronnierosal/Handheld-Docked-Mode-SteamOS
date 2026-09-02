# Supervised Ally session preparation — 2026-09-01

## Artifact readiness

This is local package evidence only. It does not prove installation, player
presence, G1 state, UI behavior, or any hardware capability.

| Role | Commit | Version | SHA-256 | Isolated validation directory |
| --- | --- | --- | --- | --- |
| Candidate | `484df70af5f31b166f32707b88292005ea90396e` | `0.2.0` | `e17357e3ea2afb5048288f76f42ec6bf0ebd83e841e9773330510207fb25fce9` | `out/validation-current-484df70` |
| Rollback baseline | `e73d249db5687f564043fe4b6f9f2fa04c2042ec` | `0.2.0` | `f9faae446cd8e61616bc0f3b3afa21961fb1b9f3fe4e87b858e1d8a9935ec519` | `out/validation-rollback-e73d249` |

The candidate was built from clean current main. The rollback was rebuilt in a
detached exact-revision worktree, not substituted from the unrelated preserved
`25802649` archive. Both embedded revisions and the paired artifact gate passed
locally with the observed baseline label `e73d249db568`.

## Session scope and stop conditions

The player must be present with a known recovery path. Stop and preserve
evidence for display/input/SSH/network loss, unexpected Steam/Decky/Gamescope
restart, or provenance mismatch. Do not suspend, reboot, unplug the G1, restart
Gamescope, or change display/GPU/audio/controller state.

## Ordered hands-on stages

1. **D2 baseline/install — G1 physically disconnected.** Confirm handheld
   display, controls, network, Steam, Decky, and SSH. Capture redacted before
   state. Install only the candidate through Decky's native lifecycle; verify
   the QAM build label, one plugin instance, hashes/RPC schema, sleep lease, and
   unload/reload return to baseline. Capture redacted after state.
2. **D2a read-only gameplay observation — G1 still disconnected.** With the
   player watching, open HDM during one ordinary internal-screen game; verify
   controller usability and deferred Troubleshooting behavior. Observe at least
   fifteen seconds without claiming performance certification.
3. **D3 named G1-attach observation — separately scheduled.** The player
   naturally attaches the G1 and retains visible control. Capture before/live
   redacted snapshots; inspect exact identity, TV/EDID, Gamescope/render state,
   game state, blockers, and sleep layers. Keep the G1 attached.

No D4 warning/support acceptance, D5 process/presentation operation, D6 sleep,
unplug, controller/audio, or display transition is in this session.
