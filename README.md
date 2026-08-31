# Handheld Dock Mode for SteamOS

Handheld Dock Mode (HDM) is a SteamOS-first project for safe, console-like
movement between handheld and TV gaming. The user should choose player concepts
such as **Portable**, **Boosted Handheld**, and **TV Docked** while HDM handles
GPU identity, display routing, Gamescope state, and safety policy.

## Status

HDM 0.2 is in development as a Decky Loader-native safety plugin. The current code inventories DRM,
Gamescope, Steam game scopes, PCI/USB4 topology, and the certified Ally X/GPD G1
profile; aggregates a typed snapshot; derives a confidence-aware mode; and holds
a crash-safe login1 sleep inhibitor plus Steam's native preflight blocker while
the G1 is attached. The preflight lifecycle and blocking/display-safety behavior
have passed supervised hardware checks; the corrected persistent warning still
needs one visible proof. HDM does not switch
displays, restart Gamescope, select GPUs, close processes, or support live eGPU
removal.

The Decky panel now uses adaptive discovery polling with privacy-safe stage
timings and can preview, copy, or save a bounded redacted HDM support bundle.
Saving requires a five-minute, single-use token for the exact JSON the player
reviewed; no frontend-supplied path is accepted.

Planned milestones:

- **0.1:** reliable read-only discovery and diagnostics
- **0.2:** sleep safety followed by safe manual Portable ↔ TV Docked transitions
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
- [Privacy-safe support bundle](docs/SUPPORT_BUNDLE.md)
- [Authoritative roadmap](docs/ROADMAP.md)
- [Deployment and validation strategy](docs/DEPLOYMENT_VALIDATION.md)
- [Remote read-only validation](docs/REMOTE_VALIDATION.md)
- [Guarded process-release contract](docs/PROCESS_RELEASE.md)
- [Durable transition journal](docs/TRANSITION_JOURNAL.md)
- [Canonical sleep workflow policy](docs/SLEEP_WORKFLOW.md)
- [Game compatibility catalog](docs/GAME_COMPATIBILITY.md)
- [eGPUBridge feature review](docs/EGPUBRIDGE_FEATURE_REVIEW.md)
- [Mid-game docking experiment](docs/experiments/MID_GAME_DOCKING.md)

## Development

The core uses the Python standard library and SteamOS's native
`systemd-inhibit` command for the bounded login1 lease.

```text
python scripts/check_architecture.py
python -m unittest discover -s tests -v
python -m compileall -q backend tests scripts
```

On SteamOS, emit a read-only diagnostic snapshot with:

```text
PYTHONPATH=backend python -m hdm.cli
```

Capture an installed Ally's redacted state without writing remote files:

```text
python scripts/remote_capture.py --host <ally-ip> --identity-file <ssh-key>
```

The Decky package uses a root delivery adapter because SteamOS protects the
Gamescope process environment. Public plugin RPCs are limited to `get_snapshot`
and the preview/token-approved support-bundle flow. Root access is limited to
observation, fixed-boundary support export, and the exact login1 sleep-inhibitor
lease; the command runner still accepts only the Steam game-scope inventory
query.

## License

MIT. See [LICENSE](LICENSE) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
