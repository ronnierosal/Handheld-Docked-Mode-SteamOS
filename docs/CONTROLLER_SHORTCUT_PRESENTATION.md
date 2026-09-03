# Controller Safe Undock presentation

Status: **Implemented (pure gesture policy plus controller-focusable Decky
fallback); Global input delivery and hardware validation required**

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

The Decky panel now supplies the reliable fallback through one
controller-focusable **Prepare G1 disconnect** control. From TV Docked it enters
the existing supervised TV-to-Portable transition. Once the player has
acknowledged that durable result and HDM freshly verifies idle Portable, the
same control becomes **Shut down to disconnect G1**. The shutdown uses a
30-second single-use backend approval and an exact fixed system power command.
It never says the cable may be removed while the Ally is powered. Guide + Y
remains dormant until SteamOS exposes a verified global input source.
