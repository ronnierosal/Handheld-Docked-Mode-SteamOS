# eGPU attach readiness

HDM's exact topology detector can observe an eGPU attach. The attach-readiness
watch is the next read-only step: it binds that candidate to the private exact
eGPU identity and waits for a newer sample before reporting a categorical
status.

It may report:

- `settling` when no newer sample exists yet;
- `waiting_for_external_display` when the same exact G1 is present but a
  verified external EDID/display is not ready;
- `waiting_for_link_health` when the exact bridge link is absent, Down, or not
  currently observable;
- `ready_idle` when the exact G1, a verified Gamescope session, one verified
  external display, an observed Up exact bridge link, and an Idle game state
  are observed;
- `game_running` when the same readiness is observed but a game is running; or
- `action_required` for an identity/session/game-state ambiguity.

`ready_idle` is a read-only observation, not an approval to dock. It neither
creates a transition plan nor changes display, GPU, controller, audio, sleep,
or power state. `game_running` deliberately does not request a restart or infer
GPU migration. A future transition owner must independently re-observe its own
exact binding, apply the unified transition engine, and require any needed
player consent.

An Up link only says the exact bridge currently reports nonzero link metrics. It
is not TV activity, render-GPU selection, bandwidth proof, controller/audio
usability, or Safe Undock authority.

The watch is implemented and simulated. It is delivered only as a categorical
field of the existing snapshot refresh, with no extra RPC, poll, event source,
or automatic attach behavior. Hardware validation requires the D3 read-only
attach stage first, followed by the separately supervised transition stages in
[Deployment and validation strategy](DEPLOYMENT_VALIDATION.md).
