# Guarded eGPU process-release contract

HDM may eventually help close ordinary same-session user processes that retain
exact G1 resources. This is a software-blocker workflow, not proof that physical
eGPU removal is safe.

## Eligibility

Only a backend-discovered process classified as `user` and `close_eligible` may
be targeted. Steam games, Gamescope, Steam, Decky, display/session services,
root, other-user, system, protected, unknown, and storage clients are never
eligible through this workflow.

The preview is generated from one complete observation with exact eGPU identity
and no mounted/swap storage. It shows bounded process names and categorical
resource kinds, but no PID, process-instance token, command line, path, or raw
hardware identity.

## Approval and revalidation

An approval is:

- short lived, bounded, and single use
- bound to graceful or force phase
- bound to exact eGPU identity and observation generation
- bound to the complete client/resource fingerprint
- bound to exact PID-plus-start-time-derived process instances internally

Consuming a token is not authority to signal immediately. HDM must collect a
new complete observation and prove the exact facts are unchanged. Before every
subsequent signal it must prove the remaining clients are only a subset of the
approved facts. After every signal it must re-scan immediately. PID reuse, a new
client, changed resources, storage use, incomplete scans, stale generation, or
changed eGPU identity stops the operation.

Force approval is a second flow. It requires a recorded prior graceful attempt,
a post-graceful observation, and a target set limited to remaining previously
attempted instances. It cannot add a process.

## Simulation status

The deterministic simulator implements:

```text
approval
  -> fresh exact revalidation
  -> one fake typed signal
  -> mandatory fresh re-scan
  -> revalidate remaining subset
  -> repeat or stop
```

It covers graceful and force actions, already-exited targets, signal rejection,
deadlines, stale or missing scans, changed clients, incomplete evidence, and
remaining blockers. Its privacy-safe audit contains sequence, phase, categorical
event/outcome, target ordinal, and resource kinds only.

The runner also writes the shared bounded transition journal from request,
observation, validation, and plan through every fake step and terminal commit,
block, or failure. The journal contains only categorical codes and observed
placement; it does not contain approval tokens, PIDs, instance IDs, process
names, eGPU identity, or commands.

Even when every observed software blocker is cleared, the result exposes
`software_blockers_cleared=true` and always keeps
`hardware_removal_authorized=false`. The certified G1 profile still requires
shutdown before disconnect.

## Remaining gates

- design and test a narrow production signal adapter
- add a Decky preview/consent flow only after the adapter review
- validate with disposable processes under direct supervision
- preserve the independent G1 teardown/removal prohibition

There is currently no production signal adapter and no process-release RPC.
