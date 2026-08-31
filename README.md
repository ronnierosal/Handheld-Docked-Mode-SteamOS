# Handheld Dock Mode for SteamOS

Handheld Dock Mode (HDM) is a SteamOS-first project for safe, console-like
movement between handheld and TV gaming. The user should choose player concepts
such as **Portable**, **Boosted Handheld**, and **TV Docked** while HDM handles
GPU identity, display routing, Gamescope state, and safety policy.

## Status

HDM is in its foundation phase. The current code defines read-only state
contracts and mode inference. It does not switch displays, restart Gamescope,
select GPUs, or support live eGPU removal.

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
- [Mid-game docking experiment](docs/experiments/MID_GAME_DOCKING.md)

## Development

The foundation uses the Python standard library only.

```text
python scripts/check_architecture.py
python -m unittest discover -s tests -v
python -m compileall -q backend tests scripts
```

## License

MIT. See [LICENSE](LICENSE) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
