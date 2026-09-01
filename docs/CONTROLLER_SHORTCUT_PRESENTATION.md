# Controller Safe Undock presentation

Status: **Implemented (pure presentation); Input delivery and hardware
validation required**

`hdm.domain.controller_shortcut_presentation` presents the existing future
**Guide + Y hold** policy without listening for controller input. It can say
that delivery is not connected, verified input is awaited, input is unverified,
the hold is incomplete, the chord did not match, or a matched chord needs the
ordinary later request path to revalidate.

The presentation deliberately omits event IDs, generations, device identity,
and input timing. A matched chord is not an undock, a Safe Undock result, or a
controller ownership claim. It does not disable/remap controllers, create a
Decky RPC, invoke the dormant relay, or initiate a transition.

A future input adapter must independently establish controller ownership,
verified/debounced event evidence, and the normal transition/revalidation path.
It requires separately supervised hardware validation.
