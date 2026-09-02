# Supervised Ally session preparation — 2026-09-01

## Artifact readiness

This is local package evidence only. It does not prove installation, player
presence, G1 state, UI behavior, or any hardware capability.

| Role | Commit | Version | SHA-256 | Isolated validation directory |
| --- | --- | --- | --- | --- |
| Candidate | `cb1696c1b622db045223c9c3846127b1fdb72bb7` | `0.2.0` | `fbf7da6fccbbed8e908a09664298f849364f9fa0380e043a953a49daba71c818` | `out/release-candidate.json` (manifest verified; create the D2 paired record before install) |
| Rollback baseline | `e73d249db5687f564043fe4b6f9f2fa04c2042ec` | `0.2.0` | `f9faae446cd8e61616bc0f3b3afa21961fb1b9f3fe4e87b858e1d8a9935ec519` | `out/validation-rollback-e73d249` |

The candidate was built from clean current main and its release-candidate
manifest verified its version, embedded revision, ZIP structure, and hash. The
rollback was rebuilt in a detached exact-revision worktree, not substituted from
the unrelated preserved `25802649` archive; its embedded revision and artifact
verifier passed locally with the observed baseline label `e73d249db568`.
This candidate supersedes the older `484df70` entry. Before D2, create the
paired candidate record from this exact archive and re-verify both artifacts.

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

## D2 result — native install observation

**Status: Remotely Observed; D2 lifecycle acceptance incomplete.** With the G1
absent and the game Idle, the player used Decky's native installer to install
the candidate above. The immediate bounded read-only capture reported
`0.2.0` / public revision `cb1696c1b622`, exactly matching the candidate,
with no collector errors, one active internal display, and one Steam,
Gamescope, and plugin-loader process. Decky remained active with zero service
restarts, logged its frontend import event, and HDM subsequently reported
Portable/Idle/certified with no blockers.

The native install did expose a stop condition for later lifecycle acceptance:
Decky waited five seconds for the prior HDM process to unload, then sent
SIGKILL before loading the candidate. This establishes neither graceful
unload/reload return-to-baseline nor controller/input/RPC health. Do not begin
D2a or attach the G1 from this result. Preserve the logs and diagnose the
shutdown timeout in a separately approved local change before advancing.
