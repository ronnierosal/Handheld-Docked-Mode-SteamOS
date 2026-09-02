# GitHub Wiki information architecture

The Wiki is the human guide; repository docs remain engineering authority. The
Wiki has not yet been published. Create pages only when useful content exists,
and link back to the owning repository contract rather than duplicating it.

## Initial publish set

| Page | Purpose | Repository authority |
|---|---|---|
| Home | Product promise, maturity, placements, safe navigation | `README.md`, `PRODUCT.md` |
| Getting Started | Current availability, prerequisites, development-only install status | `CURRENT_STATE.md`, `DEPLOYMENT_VALIDATION.md` |
| How HDM Works | Plain-language placement/health/workflow model | `PRODUCT.md`, `ARCHITECTURE.md` |
| Portable Mode | Expected internal operation and evidence | `PRODUCT.md`, `HARDWARE_SUPPORT.md` |
| Boosted Handheld Mode | Goal, current unproven status, no implied availability | `PRODUCT.md`, `CURRENT_STATE.md` |
| TV Docked Mode | Goal, current supervised status, active-vs-connected distinction | `PRODUCT.md`, `ROADMAP.md` |
| Connecting an eGPU | Safe preparation and observed attach state | `DEPLOYMENT_VALIDATION.md` |
| Disconnecting an eGPU | Current shutdown-before-disconnect policy | `SAFETY_INVARIANTS.md`, `HARDWARE_SUPPORT.md` |
| Sleep & Wake | Player guidance and known first-profile limitation | `SLEEP_WORKFLOW.md` |
| Diagnostics & Logs | How to collect bounded privacy-safe evidence | `DIAGNOSTICS.md`, `SUPPORT_BUNDLE.md` |
| Supported Hardware | Compatibility vocabulary and current profile | `HARDWARE_SUPPORT.md` |
| Troubleshooting | Symptom-to-diagnostic guidance without raw log dumping | `DIAGNOSTICS.md`, recovery docs |
| Development | Contributor entry point | `CONTRIBUTING.md`, `docs/DEVELOPMENT.md` |
| FAQ | Repeated user questions with links to authority | owning repository documents |

## Add after evidence exists

- Gaming with an eGPU
- Controllers
- Display / HDR / VRR
- Audio
- Compatibility Matrix
- ASUS ROG Ally X
- GPD G1

These pages should not be empty placeholders or imply certification before their
workflows have evidence.

## Page rules

- Start with audience, evidence date, and maturity.
- Link to the authoritative repository document near the top.
- Use player language and short procedures.
- Do not reproduce volatile commit/build/deployment values; link to
  `CURRENT_STATE.md`.
- Do not put engineering invariants, secrets, SSH coordinates, raw identities,
  or unpublished recovery procedures only in the Wiki.
- Review Wiki pages when the owning repository contract materially changes.
