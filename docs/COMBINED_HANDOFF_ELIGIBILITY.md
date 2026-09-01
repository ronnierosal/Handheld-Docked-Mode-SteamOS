# Combined handoff eligibility

The combined TV/audio/controller handoff contract consumes only explicit
categorical facts from one opaque attachment binding and one fresh observation.
It requires exact Idle game evidence, active external display, external render
GPU, external audio, external controller, and verified Portable display/audio/
built-in-controller rollback facts. Every fact must be verified and bound to the
same current generation and sample.

Missing, stale, inconsistent, changed-binding, Unknown-game, running-game, or
inactive-external evidence is ineligible. A contradiction such as active display
with non-external render is ineligible. If a future owner reports a partial
attempt and any check fails, the result is `rollback_required`, not success.

An eligible result contains only opaque current evidence for a future unified
transition engine. It is not a plan, permit, command, scheduler, RPC, or proof
that a display, GPU, audio output, or controller was changed. All mechanisms
and hardware proof remain separately supervised validation work.
