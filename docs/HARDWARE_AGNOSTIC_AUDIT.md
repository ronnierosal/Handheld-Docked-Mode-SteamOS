# Hardware-agnostic architecture audit

Audit baseline: `8d96b9c`, 2026-09-02. This classifies coupling; it does not
broaden support or authorize a refactor by itself.

## Classification

### P0 — prevents future hardware from using the normal path

- `backend/hdm/adapters/steamos/discovery.py` imports and invokes only
  `match_ally_x` and `match_gpd_g1`. Only that exact G1 becomes the external GPU
  used for link, client, readiness, placement, and support composition.
- `backend/hdm/delivery/gamescope_wrapper.py` re-resolves only the exact G1 at
  Gamescope launch. A new catalog entry alone cannot satisfy launch binding.
- This is narrower than the registry-oriented statement in `ARCHITECTURE.md`:
  the profile catalog is extensible, but central observation and mechanism
  wiring are not yet profile-driven.

### P1 — significant mechanism coupling

- `backend/hdm/adapters/steamos/sleep_inhibitor.py` produces known protected
  presence only for exact Ally + G1.
- `backend/hdm/adapters/steamos/game_render_binding.py` and its construction in
  `main.py` hardwire Ally internal and G1 render resolvers.
- `backend/hdm/adapters/drm_engine_activity.py` accepts only `amdgpu` activity.
- `backend/hdm/adapters/steamos/drm.py` classifies only `eDP-*` as internal,
  while the Gamescope wrapper also recognizes `DSI-*` and `LVDS-*`.
- Production construction in `main.py` wires G1-specific sleep and wake
  discovery directly.

### P2 — profile/configuration or terminology candidates

- Exact G1 topology and USB4 constraints in `profiles/gpd_g1.py` are correctly
  isolated; keep them profile-local.
- `application/support_bundle.py` checks the literal Ally profile ID instead of
  resolved certification status.
- Some player-facing strings in `src/refresh-policy.ts` and `src/index.tsx` say
  G1 where the product contract calls for eGPU/handheld terminology.
- Some pure domain names use G1 for generic attachment semantics.
- Ally-named deployment scripts are acceptable first-profile tooling; fixed
  user/path choices should become install-profile inputs only when another
  real target requires them.

### P3 — intentional certification evidence

- Exact Ally DMI and G1 PCI/USB4/driver IDs in `profiles/ally_x.py` and
  `profiles/gpd_g1.py` are appropriate.
- Tests deliberately use varying `card*`, HDMI, eDP, and PCI address fixtures;
  they prove rediscovery and are not production hard-coding.
- DRM, PCI, USB4, controller, and audio inventories use runtime enumeration.
- SteamOS sysfs/procfs paths are platform-adapter assumptions, not device-model
  assumptions.

## Minimal refactor direction

1. Define one narrow resolved runtime-profile contract consumed by discovery,
   sleep guard, render binding, and Gamescope launch.
2. Keep Ally/G1 exact matchers as the first implementations.
3. Add one synthetic second-profile test before changing production behavior;
   do not claim that synthetic profile as supported hardware.
4. Centralize internal connector classification for eDP/DSI/LVDS.
5. Move AMD driver/vendor requirements behind selected profile capabilities,
   preserving exact G1 validation.
6. Use generic player wording while retaining exact model names in diagnostics,
   compatibility, and certification pages.

This is a Phase 5 change because it touches the hardware journey's runtime path.
Coordinate with that driver and keep each refactor independently testable.
