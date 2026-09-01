# Recovery explanation policy

Status: **Implemented (pure frontend policy); delivery and hardware validation
required**

`src/recovery-explanation.ts` maps only public categorical link, interrupted-
sleep, and portable-recovery states to calm player explanations. It remembers
one public kind/state key to suppress repeated refreshes; stable link evidence
silently clears a prior link episode.

The policy neither collects evidence nor delivers a notification. It omits raw
codes and all device/game/account/process identities. Its wording explicitly
does not claim link quality, hardware recovery, game survival, a crash, safe
unplug, or automatic relaunch.

Any future delivery owner must independently decide when a visible surface is
appropriate and remain bounded. This module adds no transport, watcher, poller,
system action, controller action, game action, or hardware claim.
