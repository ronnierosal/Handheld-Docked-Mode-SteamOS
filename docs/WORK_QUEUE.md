# HDM worker queue

This is the current coordination source of truth for bounded local work. It
does not replace executable behavior, [the roadmap](ROADMAP.md), or the
[safety invariants](SAFETY_INVARIANTS.md). The North Star is console-simple,
games-first SteamOS: HDM stays light, mostly dormant, event-driven where
practical, and never trades safety or game performance for automation. Licensing
remains GPLv3+ for community use and separately negotiated for commercial/OEM
use; see [Licensing](LICENSING.md).

## Rules

- An idle worker may take the first unblocked item only when it is within its
  authority and can remain bounded, reversible, and independently verifiable.
  Otherwise record the blocker and take the next safe item.
- **Implemented**, **Simulated**, **Remotely Observed**, **Hardware Validation
  Required**, **Hardware Validated**, and **Certified** are distinct statuses.
  Code or capture never upgrades hardware validation.
- No deployment, sleep/reboot, Gamescope restart, display/GPU/audio/controller
  mutation, USB4/PCIe reset, process signaling, or G1 removal without the
  explicit supervised gate. Read-only capture does not authorize a transition.
- This queue enables fast continuation; it does not schedule autonomous work.
  A worker must be triggered, or a separately authorized future heartbeat must
  be active.

## Ordered queue

### 1. Ally ↔ G1 end-to-end dock, play, sleep, and undock journey

**Status: Proposed parent journey.** It is the overarching player-facing focus,
not a claim that the journey is currently supported. HDM must never promise
live GPU migration or game survival. No disruptive hardware action is allowed
without explicit supervision, and no safe-to-unplug result is allowed without
verified clients, topology, display, and input evidence. Read-only Ally evidence
is permitted.

| Priority | Bounded sub-item and owner | Status | Acceptance evidence |
| --- | --- | --- | --- |
| 1.1 | Attach detection and health. Owner: mode/link worker. | **Implemented (local, link-gated):** `ready_idle` now also requires an observed Up exact bridge link; Down/unknown remains waiting. End-to-end behavior is **Hardware Validation Required**. | Exact attach/health replay tests and redacted read-only supported-profile evidence. |
| 1.2 | Game-open deferred dock intent. Owner: transition worker. | **Implemented (pure, local-only):** direct player intent may expire, cancel, or invalidate while a game runs, then yield only a fresh idle eligibility handoff. No automatic transition authority exists. | Deterministic creation/cancellation/expiry/binding-change/unknown-game/idle-handoff tests; later supervised proof only after a reviewed mechanism. |
| 1.3 | Game-closed verified TV, audio, and controller handoff. Owner: transition/peripheral worker. | **Implemented (pure eligibility/rollback contract):** only fresh, consistent, verified Idle TV/render/audio/controller and Portable rollback facts can become non-authorizing eligible; partial failure requires rollback. Handoff is **Hardware Validation Required**. | Exact idle, display, audio, controller, and rollback evidence in a supervised test. |
| 1.4 | Five-second post-game prepared-docked-idle state. Owner: transition worker. | **Implemented (pure revalidation contract):** two fresh consistent Idle samples with the same attachment/generation and a new sample at >=5 seconds can yield non-authorizing prepared evidence. No timer or prepared-dock authority exists. | Deterministic under/exact/over-boundary and invalidation tests, then supervised observation without a running game. |
| 1.5 | Safe Undock readiness scans. Owner: recovery worker. | **Implemented (pure read-only revalidation contract):** complete fresh opaque-bound client/topology/game/Portable-fallback/display facts can be only `ready_for_revalidation`; any gap stays insufficient/not-ready/invalidated. Physical unplug safety is **Hardware Validation Required**. | Fresh exact client, storage, topology, display, and input scans; incomplete evidence remains unsafe. |
| 1.6 | Human-acknowledged Safe Undock result presentation. Owner: recovery worker. | **Implemented (pure, local-only):** Stage 1.5 revalidation-bound evidence can be presented only as insufficient, not-ready, revalidate-required, or eligible to begin supervised physical validation. It never says safe-to-unplug or takes action. | Deterministic acknowledgement/stale-binding/generation/sample invalidation tests; every physical test remains separately approved and **Hardware Validation Required**. |
| 1.7 | Unexpected removal recovery to handheld. Owner: recovery worker. | **Implemented (pure, local-only assessment):** fresh opaque-bound before/after bridge/topology loss plus verified internal display/input/audio can report only portable-fallback evidence. Unknown, stale, changed, or contradictory facts fail closed; no recovery/relaunch action exists. Hardware recovery is **Hardware Validation Required**. | Deterministic loss, fallback, missing-signal, unknown-game, stale/binding-change, and contradiction tests; separately approved supervised handheld recovery scenario. |
| 1.8 | Sleep/wake with G1 present or missing, with honest game-relaunch policy. Owner: sleep/recovery worker. | **Implemented (pure, local-only eligibility):** verified handheld fallback, stopped-game observation, clear risks, fresh evidence, and explicit opt-in can only label a future relaunch flow eligible. Unknown/running game, risks, repeated failure, stale/contradictory evidence, or uncertain preference block it. Wake behavior and relaunch are **Hardware Validation Required**. | Deterministic recovery, first-prompt, opt-in/out, risk, failure-limit, stale, and contradiction tests; separately approved supervised scenarios. No crash or relaunch claim from passive evidence. |

### Supporting queue

| Priority | Work item and owner | Status | Acceptance evidence |
| --- | --- | --- | --- |
| 2 | Mode/link health: improve fail-closed usability signals and bounded link-instability diagnostics. Owner: next safe worker. | **Implemented** foundation; hardware link quality is **Hardware Validation Required**. | Pure/replay tests; privacy-safe snapshot/UI checks; supported-profile read-only capture when useful. |
| 3 | Recovery and unified transitions: deterministic replay, journal, rollback, Portable recovery, and Safe Undock guards. Owner: transition/recovery worker. | Policy and replay are **Implemented/Simulated**; live execution is **Hardware Validation Required**. | Architecture + deterministic failure tests; a separately approved supervised run for any mechanism. |
| 4 | Offline Readiness delivery: review a local Steam/launcher source, then surface only fresh categorical results. Owner: evidence/UI worker. | Classifier/admission contract and **read-only UI presentation** are **Implemented**; current snapshot delivery, source review, and collection authority are not. UI accepts only optional public categorical status/reason payload and says “Not connected” when unwired. | Privacy review, declared/benchmarked cost, idle-only/defer/freshness tests, reviewed read-only delivery; no account/AppID/title/path in delivery. |
| 5 | Navigation/UI cleanup: keep Quick Access compact, controller-friendly, and non-authorizing. Owner: frontend worker. | **Implemented (read-only UI):** compact health plus deferred/prepare/Safe Undock/recovery journey rows, with controller-focusable details on demand and fail-closed "Not connected" values until snapshot wiring exists. Live evidence wiring and hardware behavior are **Hardware Validation Required**. | Frontend accessibility/navigation tests, typecheck/build, reviewed read-only schema delivery, and a maintainer-visible package review before install. |
| 6 | Performance/resource measurement: measure snapshot and optional-observer overhead; retain only event-driven or budgeted work. Owner: performance worker. | Telemetry admission, UI cadence, and **pure one-sample overhead assessment/reporting** are **Implemented**; collector and actual supported-profile measurement are pending. Reports are identity-free and game impact remains Unknown. | Reproducible bounded existing-work timing plus player-observed game-impact evidence on the supported profile; no meaningful regression. |

## Required checkpoint check-in

Record each meaningful checkpoint in [Operator handoff](OPERATOR_HANDOFF.md)
and, when status/dependencies change, [Roadmap](ROADMAP.md):

```text
Change: <bounded files/behavior; state implemented vs proposal>
Verification: <exact commands/tests/build and result>
Hardware evidence: <none | redacted read-only capture | supervised validation>
Blockers: <authority, safety, or evidence gap>
Next safe task: <one concrete, bounded item>
```

Exclude secrets, raw device identities, and transient logs.

## Integration

Commit only small, coherent, verified slices. Before integration, inspect the
diff and relevant tests, confirm clean ancestry and no unrelated worktree
changes, then fast-forward or make the smallest safe merge. Resolve conflicts
deliberately, record the check-in, and do not leave completed worker commits
queued without a reason.
