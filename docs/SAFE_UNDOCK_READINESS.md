# Safe Undock readiness

This pure read-only contract consolidates explicit facts for a *future*
supervised revalidation: exact attachment and topology, complete current client
scan with no active/protected clients, exactly Idle game, active Portable
display/render/audio/built-in controller, and inactive external display. Every
fact must be verified and bound to the same opaque attachment, generation, and
sample.

Missing or Unknown game/topology/client evidence is `evidence_insufficient`.
Known active game, protected or active clients, missing Portable fallback, or
still-active external display is `not_ready`. Changed attachment or stale/
inconsistent observation identity is `invalidated`.

`ready_for_revalidation` is not “safe to unplug.” It only returns opaque current
evidence to a future owner, which must re-observe and pass separate supervised
validation. This contract has no physical-removal claim, transition plan,
approval, process/helper/device action, RPC, poller, or scheduler.
