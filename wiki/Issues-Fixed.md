# Issues fixed

**Audience:** testers, maintainers, and contributors<br>
**Evidence reviewed:** 2026-09-02<br>
**Maturity:** selected recent fixes with their actual evidence level

This page records useful outcomes without treating a merged code change as
hardware certification. The repository
[current state](https://github.com/ronnierosal/Handheld-Docked-Mode-SteamOS/blob/main/docs/CURRENT_STATE.md)
and [roadmap](https://github.com/ronnierosal/Handheld-Docked-Mode-SteamOS/blob/main/docs/ROADMAP.md)
own current status.

| Issue | Fix | Evidence | Remaining gate |
|---|---|---|---|
| SteamOS reported PCIe width in a valid bare form that readiness rejected | Parser accepts the observed SteamOS form while preserving validation | Implemented with regression coverage | Does not expand certified hardware |
| Exact-profile automatic docking had no production path | Added a profile-gated path using the existing transition and rollback boundaries | Hardware tested once: TV active and RX 7600M XT selected | Repeated journey validation remains |
| A terminal shared journal could be offered to the wrong acknowledgement owner | Route acknowledgement by the journal's categorical owner and keep unknown journals blocked | Installed; exact presentation acknowledgement and retry observed | Continue regression coverage across owners |
| Gamescope launch binding did not match the writer's boot identity | Preserve raw boot identity only in memory for the private binding hash; serialize only the hashed identity | Implemented; repeat hardware attempt passed the original mismatch | The repeat exposed the separate file-permission issue |
| The Gamescope user could not read the root-created launch config | Write the identity-minimized config root-owned and read-only to ordinary users | Hardware tested once: Steam visible on the TV and transition committed | Repeated journey validation remains |
| TV docking succeeded but audio stayed on the Ally | Resolve the exact G1 HDMI loopback sink just in time, verify selection, and retain the captured Portable sink for rollback | Direct TV selection hardware tested; guarded automatic path implemented and simulated | Automatic selection and Portable restoration need watched hardware proof |
| Generic player and support wording embedded the first eGPU/host names | Use capability-neutral player wording and profile-resolution evidence, retaining legacy preference migration | Implemented with an alternate-profile regression test | Exact names remain in profile and compatibility surfaces |
| Current docs exposed a maintainer checkout path and tests used realistic-looking personal/network placeholders | Removed the current path and replaced fixtures with explicit synthetic/documentation values | Fixed in current tracked files; privacy audit completed | Historical commits still retain old private LAN/path metadata |
| Common secret-file patterns were not ignored | Added repository hygiene ignores for common environment and key files | Fixed in current repository | Ignores supplement, but do not replace, review and secret scanning |

## Open high-priority coupling

The privacy and hardware audit also identified four P1 seams that are not fixed
yet: central discovery recognizes only the first profiles; sleep protection is
wired to first-profile presence; internal GPU/panel classification assumes boot
VGA and eDP; and launch/render composition is Ally/G1/AMD-specific. These should
be resolved as small profile-driven changes with synthetic alternate-profile
tests, coordinated with the active hardware work.

See the full
[hardware and privacy audit](https://github.com/ronnierosal/Handheld-Docked-Mode-SteamOS/blob/main/docs/HARDWARE_PRIVACY_AUDIT_2026-09-02.md).

The complete causal chain for the Ally X/GPD G1 session is documented in
[Ally X and GPD G1 docking incident](Ally-X-and-GPD-G1-Docking-Incident).
