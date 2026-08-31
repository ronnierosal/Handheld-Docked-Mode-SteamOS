# Durable transition journal

HDM's transition journal is the crash-recovery authority for future mutating
operations. It records what was requested, observed, validated, planned,
attempted, verified, recovered, and committed. It does not infer success from a
mechanism call.

## Schema and privacy

The immutable schema is versioned and bounded to 128 entries. Entries have a
contiguous sequence, categorical event/code/details, workflow phase, observed
placement, and timestamp supplied by the caller. Invalid event order, unknown
fields, private/free-form details, post-terminal appends, and over-bound history
fail closed.

The journal must not contain:

- commands or arguments
- paths
- PIDs or process-instance IDs
- approval tokens
- raw hardware or account identity
- hostnames or network information

## Fixed-path store

The dormant file adapter stores one journal as `active-transition.json` under an
absolute backend-owned state directory. No frontend path or filename is
accepted.

The production composition has a separate fixed state-root boundary at
`/var/lib/handheld-dock-mode`. It creates only that final directory from the
existing real `/var/lib` parent, requires a POSIX root process, and accepts only
a real root-owned mode-0700 directory below a real root-owned, non-writable
parent. Symlinks, alternate leaf names, group/world-writable parents, non-root
ownership, and permission drift fail closed. The user-owned Gamescope
launch-config directory is never journal authority.

Save behavior:

1. Validate the existing journal, if any.
2. Require the same operation and request IDs.
3. Require the existing history to be an exact prefix of the replacement.
4. Encode strict bounded JSON.
5. Create a mode-0600 no-follow temporary file in the same directory.
6. Flush and `fsync` the file.
7. Atomically replace the fixed target.
8. `fsync` the containing directory where supported.

An injected replace failure leaves the prior journal intact and removes the
known temporary file. A different operation, regressed/divergent history,
corrupt file, unsupported schema, target symlink, or unavailable/symlink state
directory is rejected.

Only a matching terminal operation may be cleared. Incomplete state cannot be
discarded through the store.

## Runtime orchestration

The dormant runtime orchestrator persists every journal state through this
store. In particular, `step_started` must be durable before it calls a
mechanism. It re-observes the exact bound profile/GPU/display and game state
immediately before that point, then accepts a result only after a new snapshot
verifies the requested placement inside the deadline.

Apply failure, verification timeout, or inability to durably commit causes an
idempotent source-placement recovery attempt. If a restart finds an incomplete
journal before `step_started`, it terminals the abandoned request without a
mechanism call. If a step may have started, it attempts source recovery using a
fresh observation and records verified recovery or Action Required. It never
continues the interrupted target request.

The exact transition binding and experimental approval identity are not written
to this privacy-safe journal.

## Current boundary

The store is now constructed by Decky for guarded process release under the
root-owned state directory. Process execution durably records `step_started`
before signaling, and startup recovery terminalizes an incomplete release
without repeating a signal. The presentation runtime orchestrator and mechanism
remain unconstructed; no display/GPU transition endpoint is enabled.

The canonical sleep coordinator uses the same port in deterministic tests and
persists each active stage before returning its directives. It remains unwired
from Decky. An interrupted journal never resumes an original sleep request after
restart; verified Portable recovery is terminal recovery evidence only, while
unknown or docked state fails closed into Action Required.

The journal now has strict `substep_started` / `substep_verified` events inside
an active parent step. Canonical sleep uses them for guarded process release:
every signal is preceded by a durable identity-free substep, every rescan closes
that substep, and graceful plus force phases remain inside the original sleep
operation. A second authoritative process journal is never opened. The sleep
child target bound is 27 so the worst-case two-phase release plus all remaining
sleep/recovery events still fit the 128-entry journal.

The guarded game-close child uses the same substep ordering. It persists an
identity-free `game.close_substep_started` event before invoking its injected
mechanism and closes the substep only after a fresh exact observation proves
the game Idle. Steam AppID, scope names, approval tokens, and mechanism details
are never journal fields. Any close failure terminalizes the parent sleep
transaction as Action Required; no production game-close adapter is wired.

Every recovery/acknowledgement service first verifies the journal's categorical
owner marker. Process-release startup recovery cannot terminalize, clear, or
misreport a sleep or other foreign transaction; it returns a foreign-journal
blocker without modifying the file.
