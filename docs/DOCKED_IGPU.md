# Docked-iGPU workflow

Docked-iGPU is a first-class observed placement: the exact internal GPU renders
while the exact external display is active. It is not inferred merely because a
G1 and TV are connected.

## Implemented, dormant pieces

- The boot-scoped Gamescope config can explicitly select the TV connector and
  internal GPU.
- The existing supervised durable transition engine can promote exact idle
  Docked-iGPU to Docked-eGPU.
- The same engine can recover to Docked-iGPU after failed promotion.
- A bounded read-only watcher can arm only around one exact running Steam game,
  bracket its initial state with two game samples, and recognize its natural
  exit only after two exact Idle samples surround a fresh Docked-iGPU snapshot.
- The watcher cancels on another game, placement change, or expiry and enters
  Action Required on unknown identity/profile evidence.
- Public watcher payloads omit AppID, scopes, profile IDs, eGPU identity, and
  observation generations.
- Support Preview can now run one explicit bounded, read-only comparison of the
  exact game's DRM engine activity on the independently re-resolved Ally
  internal GPU and G1. Only categorical, identity-free results enter the
  support event log; this does not arm or execute a transition.

The watcher emits only `promotion_ready`. It cannot create approval, write
config, restart Gamescope, or invoke the transition engine. Current Ally X/G1
display handoff remains Experimental, so the supervised path still needs the
existing explicit short-lived approval.

An in-memory backend facade now composes that ready state with supervised
preview. Delivery supplies only the opaque watch ID. The facade retrieves the
private ready generation, requires the transition preview to observe that exact
generation and Docked-iGPU placement, and retains the watch on inspection or a
blocked preview. It consumes the watch only after explicit confirmation
produces a short-lived approval token. It does not execute that token and has no
Decky RPC.

## Remaining gates

- prove on hardware that a running iGPU game can be presented on the TV through
  the G1 without changing game or Gamescope identity
- use a complete one-shot Support Preview comparison on the current candidate
  to observe internal activity and no G1 activity during that supervised
  experiment; either Unknown result is incomplete and proves neither absence
  nor placement
- add a backend-owned scheduler and production lifecycle for the in-memory
  watcher
- wire the opaque facade through a reviewed Decky delivery path
- verify Docked-iGPU rollback before enabling any automatic trigger
- after transition, use exact DRM engine activity to prove the next game uses
  the G1

None of these pieces certifies live GPU migration. HDM still never attempts to
move a running workload between GPUs.
