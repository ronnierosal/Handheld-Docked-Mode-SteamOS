# Journey status delivery validation

Status: **Implemented (frontend boundary validation); backend delivery required**

Quick Access now sanitizes the optional `journey` snapshot field before status
presentation. It accepts only recognized public categorical states, schema-1
link/offline shapes, and the bounded link current-state values. Raw codes,
offline reason lists, and all extra fields are discarded before UI state.

Malformed, incomplete, or future values are omitted. The existing Journey UI
therefore remains fail-closed as “Not connected”; validation does not turn an
optional payload into a hardware conclusion.

This adds no snapshot producer, collector, RPC, storage, action, timer, or
hardware behavior. A future adapter must still provide a reviewed read-only
public payload and preserve the same privacy/freshness boundaries.
