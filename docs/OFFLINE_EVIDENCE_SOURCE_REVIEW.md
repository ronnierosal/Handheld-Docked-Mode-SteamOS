# Offline Readiness source review boundary

Status: **Implemented (pure review contract); source implementation required**

Before a future Offline Readiness source can reach the existing collection
admission gate, it must supply an identity-free declaration: local Steam or
local launcher metadata, read-only behavior, no network, no persistence,
identity minimization, and a bounded unique set of categorical evidence fields.
The declaration contains no command, path, title, AppID, account, or collected
value.

The review accepts only a local/read-only/non-networked/non-persistent/minimized
declaration. Its approval then composes with the existing reviewed, benchmarked,
bounded-cost, freshness, and game-aware collection admission policy. Rejection
is categorical and fail-closed.

This is not a Steam or launcher collector. It opens no files, calls no process,
stores no data, schedules no work, and creates no UI or launch authority. A
future source still needs separate implementation review and measurement.
