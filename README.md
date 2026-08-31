# Handheld Dock Mode for SteamOS

Handheld Dock Mode (HDM) is a SteamOS-first project for safe, console-like
movement between handheld and TV gaming. The user should choose player concepts
such as **Portable**, **Boosted Handheld**, and **TV Docked** while HDM handles
GPU identity, display routing, Gamescope state, and safety policy.

## Status

HDM 0.1 read-only discovery is available as a Decky Loader diagnostics plugin. The current code inventories DRM,
Gamescope, Steam game scopes, PCI/USB4 topology, and the certified Ally X/GPD G1
profile; aggregates a typed snapshot; and derives a confidence-aware mode. It
does not switch displays, restart Gamescope, select GPUs, or support live eGPU
removal.

Planned milestones:

- **0.1:** reliable read-only discovery and diagnostics
- **0.2:** safe manual Portable ↔ TV Docked transitions
- **0.3:** policy-gated automatic docking

The first certified target is an ASUS ROG Ally X running SteamOS with a GPD G1
RX 7600M XT and a TV connected directly to the G1.

## Design

Start with:

- [Product definition](docs/PRODUCT.md)
- [Safety invariants](docs/SAFETY_INVARIANTS.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Hardware support](docs/HARDWARE_SUPPORT.md)
- [Read-only diagnostics](docs/DIAGNOSTICS.md)
- [eGPUBridge feature review](docs/EGPUBRIDGE_FEATURE_REVIEW.md)
- [Mid-game docking experiment](docs/experiments/MID_GAME_DOCKING.md)

## Development

The foundation uses the Python standard library only.

```text
python scripts/check_architecture.py
python -m unittest discover -s tests -v
python -m compileall -q backend tests scripts
```

On SteamOS, emit a read-only diagnostic snapshot with:

```text
PYTHONPATH=backend python -m hdm.cli
```

The Decky package uses a root delivery adapter because SteamOS protects the
Gamescope process environment. Root access is limited to observation: the only
public plugin RPC is `get_snapshot`, and the command runner accepts only the
Steam game-scope inventory query.

## License

MIT. See [LICENSE](LICENSE) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
