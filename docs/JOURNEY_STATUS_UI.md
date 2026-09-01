# Journey status UI

Status: **Implemented (read-only presentation); Live evidence wiring and
Hardware Validation Required**

The Quick Access panel now keeps health in its existing at-a-glance section and
adds a compact Journey status section for deferred dock intent, prepared idle,
Safe Undock evidence, unexpected-removal recovery, and bounded link evidence.
Technical explanation is behind an explicit controller-focusable "Open journey
details" control.

The current snapshot schema does not deliver these local classifier results.
Until a future reviewed read-only adapter supplies them, each row says "Not
connected"; that is deliberate and is not a missing-hardware, safe-undock, or
recovery conclusion. Unknown future states are treated the same way.

The optional link-evidence row can show only stable observed state, a state
change, or incomplete evidence. It never rates throughput, cable quality, or
performance and does not produce a link-health recovery/removal conclusion.

The panel has no action control, new RPC, timer, autoplay, polling policy, or
hardware validation claim. Returning to the top collapses journey and
troubleshooting details, scrolls only its owning Steam panel, and restores focus
to the first in-panel native control without sending controller focus to QAM
Back.
