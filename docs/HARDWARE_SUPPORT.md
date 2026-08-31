# Hardware support model

## Support tiers

- **Certified:** directly tested with captured evidence and bounded known behavior.
- **Compatible:** expected to work through standard mechanisms but not fully
  validated on hardware.
- **Experimental:** detected and intentionally available for controlled testing.
- **Unsupported:** blocked because required identity, safety, or mechanism is absent.

## First certified profile

| Component | Identity |
|---|---|
| Host | ASUS ROG Ally X running SteamOS |
| eGPU | GPD G1, AMD Radeon RX 7600M XT (`1002:7480`) |
| HDMI audio | AMD `1002:ab30` |
| Removable bridge | Intel Titan Ridge `8086:15ef` |
| xHCI | Intel `8086:15f0` |
| Observed USB4 device | Intel Tapex Creek |

The complete topology and privacy-preserving USB4 identity must be verified; the
GPU PCI ID alone does not prove that the device is the certified G1. The live G1
topology contains one top-level removable Titan Ridge bridge and multiple
downstream `8086:15ef` bridge functions. The USB4 host-router record has no
external-device identity and is not counted as a connected peripheral; any
other unidentified authorized USB4 node remains a certification blocker.

## Validated reference behavior

- Internal and G1-connected TV discovery
- Portable ↔ TV output transitions in approximately 4–6 seconds
- Exact G1 identity persistence without storing its raw USB4 unique ID
- Fail-closed Steam game detection
- Running-game transition blocking without restarting Gamescope
- Idempotent internal restore

## Unproven or unsupported

- G1 rendering to the Ally internal panel remains unproven.
- Mid-game iGPU presentation on the TV remains a research case.
- Physical live eGPU removal is unsupported.
- Other hosts, eGPUs, and SteamOS versions are not certified by inference.

All addresses and connector names observed during validation are ephemeral and
must be rediscovered after boot, reconnect, and resume.

See [HDM 0.1 read-only hardware validation](HARDWARE_VALIDATION_2026-08-31.md)
for the first native snapshot result and its privilege-boundary finding.
