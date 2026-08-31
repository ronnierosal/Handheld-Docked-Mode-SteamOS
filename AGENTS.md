# Handheld Dock Mode Instructions

## Project identity

HDM is a SteamOS-first, safety-critical dock-mode controller. It is a new
project; eGPUBridge is reference evidence, not the architecture to reproduce.

## Sources of truth

- Product scope: `docs/PRODUCT.md`
- Non-negotiable safety rules: `docs/SAFETY_INVARIANTS.md`
- Component and state design: `docs/ARCHITECTURE.md`
- Certified hardware claims: `docs/HARDWARE_SUPPORT.md`
- Diagnostics contract: `docs/DIAGNOSTICS.md`
- Current executable behavior: code plus tests; docs and memory never override it

## Required rules

- Keep physical connection, render GPU, display target, Gamescope state, and
  running-game state independent.
- Never hard-code DRM card numbers, connector suffixes, or PCI bus addresses.
- Unknown GPU identity, game state, or transition readiness fails closed.
- Never migrate a running workload between GPUs or claim live eGPU removal is safe.
- Manual and automatic requests must eventually use one transition engine.
- Keep `backend/hdm/domain` pure: no filesystem, subprocess, network, or OS calls.
- Milestone 0.1 is read-only. Do not add display/GPU mutation without an explicit
  milestone decision and corresponding safety tests.

## Workflow

Run before handing off changes:

```text
python scripts/check_architecture.py
python -m unittest discover -s tests -v
python -m compileall -q backend tests scripts
```

Hardware-affecting work additionally requires redacted before/live/after evidence
and supervised validation on a supported profile.
