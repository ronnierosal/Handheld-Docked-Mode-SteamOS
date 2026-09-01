# Journey status UI

Status: **Implemented (read-only presentation); Live evidence wiring and
Hardware Validation Required**

The Quick Access panel now keeps health in its existing at-a-glance section and
adds a compact Journey status section for deferred dock intent, prepared idle,
Safe Undock evidence, and unexpected-removal recovery. Technical explanation is
behind an explicit controller-focusable "Open journey details" control.

The current snapshot schema does not deliver these local classifier results.
Until a future reviewed read-only adapter supplies them, each row says "Not
connected"; that is deliberate and is not a missing-hardware, safe-undock, or
recovery conclusion. Unknown future states are treated the same way.

The panel has no action control, new RPC, timer, autoplay, polling policy, or
hardware validation claim. Returning to the top collapses journey and
troubleshooting details, scrolls only its owning Steam panel, and restores focus
to the first in-panel native control without sending controller focus to QAM
Back.
