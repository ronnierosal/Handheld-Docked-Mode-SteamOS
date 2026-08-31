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

## Current boundary

The store and its persistence port are implemented and unit tested, but the
Decky plugin does not construct them. No transition endpoint is enabled. Wiring
the store belongs to the first approved live transition and must include startup
recovery policy and supervised failure testing.

