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

| Priority | Work item and owner | Status | Acceptance evidence |
| --- | --- | --- | --- |
| 1 | Mode/link health: improve fail-closed usability signals and bounded link-instability diagnostics. Owner: next safe worker. | **Implemented** foundation; hardware link quality is **Hardware Validation Required**. | Pure/replay tests; privacy-safe snapshot/UI checks; supported-profile read-only capture when useful. |
| 2 | Recovery and unified transitions: deterministic replay, journal, rollback, Portable recovery, and Safe Undock guards. Owner: transition/recovery worker. | Policy and replay are **Implemented/Simulated**; live execution is **Hardware Validation Required**. | Architecture + deterministic failure tests; a separately approved supervised run for any mechanism. |
| 3 | Offline Readiness delivery: review a local Steam/launcher source, then surface only fresh categorical results. Owner: evidence/UI worker. | Classifier and admission contract are **Implemented**; source, UI, and collection authority are not. | Privacy review, declared/benchmarked cost, idle-only/defer tests, freshness tests; no account/AppID/title/path in delivery. |
| 4 | Navigation/UI cleanup: keep Quick Access compact, controller-friendly, and non-authorizing. Owner: frontend worker. | Existing compact/status and troubleshooting split is **Implemented** locally. | Frontend tests, typecheck/build, and a maintainer-visible package review before install. |
| 5 | Performance/resource measurement: measure snapshot and optional-observer overhead; retain only event-driven or budgeted work. Owner: performance worker. | Telemetry admission and UI cadence policy are **Implemented**; real collector measurement is pending. | Reproducible timing evidence on the supported profile; no meaningful game-impact regression. |

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
