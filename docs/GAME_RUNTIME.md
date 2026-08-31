# Active game runtime evidence

HDM has a dormant read-only adapter for enriching one already exact Steam game
scope identity with private process/runtime evidence. It does not close,
relaunch, signal, or otherwise affect a game.

## Evidence boundary

The input is a backend-derived exact Steam AppID and bounded set of recognized
systemd scope names. The adapter then:

1. finds every exact scope below the fixed user-service cgroup root
2. reads the bounded union of `cgroup.procs`
3. reads each process twice from procfs and binds PID plus start time
4. records parent PID and executable basename privately
5. recognizes Proton only from allowlisted environment-key presence
6. produces a stable semantic generation and a distinct collection sample

Missing scopes, duplicate scope identities, an invalid or oversized PID set,
process disappearance/PID reuse, an AppID conflict, unreadable procfs evidence,
or an oversized environment all produce one categorical Unknown result. Partial
process graphs are discarded.

The adapter retains no environment values or executable paths. PID, parent,
start time, scope, and executable basename remain private backend evidence and
must not enter public snapshots, support bundles, or the transition journal.

## Current limits

This slice proves exact scope process identity, parent/launcher relationships,
and native-versus-Proton classification only. It does not yet prove:

- Steam title or game version
- a specific Proton build/version
- launcher child ownership outside the exact scope set
- actual rendering GPU for the game
- save behavior, relaunch behavior, or compatibility status

No Decky RPC constructs this adapter yet. A future consumer must revalidate the
exact AppID/scopes and a fresh runtime generation before using it in a guarded
operation.
