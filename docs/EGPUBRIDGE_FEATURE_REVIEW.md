# eGPUBridge parity audit

Audit baseline: HDM `8d96b9c`, eGPUBridge frozen hardware reference
`ef04f65f`, reviewed 2026-09-02.

eGPUBridge is hardware and UX evidence, not HDM's architecture. A capability is
not preserved merely because similar code or a deterministic test exists; the
HDM evidence column states what is actually present.

## Status vocabulary

- **Preserved:** equivalent user value exists through HDM's architecture.
- **Improved in HDM:** the capability exists with a clearer or safer contract.
- **Intentionally different:** HDM solves the need differently.
- **Missing / candidate:** useful evidence exists, but HDM does not yet deliver it.
- **Not applicable:** outside HDM's product or platform boundary.

## Capability ledger

| eGPUBridge capability | HDM classification | HDM evidence / decision |
|---|---|---|
| DRM, Gamescope, Steam-game, PCI, and USB4 discovery | Improved in HDM | Independent typed observations in SteamOS adapters; exact-profile composition; runtime card/connector/address rediscovery; deterministic fixtures and first-profile read-only evidence. |
| GPU/eGPU identity | Improved in HDM | Conservative Ally/G1 profiles require full topology and opaque USB4 identity; incomplete/ambiguous identity fails closed. Central multi-profile wiring remains a P0 audit gap. |
| Internal/external display detection | Improved in HDM | Connected output and live active Gamescope target are separate facts. Internal connector classification needs eDP/DSI/LVDS consistency. |
| Native Decky status UI | Improved in HDM | Typed RPC, native controls, bounded polling, placement/health/game separation, progressive troubleshooting. See `UI_SPEC.md`. |
| One-tap TV switch | Missing / candidate | One player-watched supervised HDM path is implemented/simulated. Corrected native path still requires fresh Ally/G1/TV proof; automatic docking is unavailable. |
| Restore Internal | Preserved, hardware proof pending | Portable recovery policy, journal, wrapper failback, and orchestrator verification exist; native corrected path still needs supervised proof. |
| Idempotent switch | Improved in HDM | Transition policy skips already verified target state and binds requests to fresh observations; hardware proof remains workflow-specific. |
| Running-game guard | Improved in HDM | Running or unknown game state blocks disruptive transition; no executable-name-only guess. |
| Switch ordering and verification | Improved in HDM | Detect → Validate → Plan → Prepare → Apply → Verify → Commit with journaled rollback; eGPUBridge's proven ordering informed the mechanism. |
| Gamescope handling | Intentionally different | HDM uses a narrow prepared integration, boot-scoped configuration, exact user/session discovery, and a supervised transition boundary rather than the monolithic legacy backend. |
| Bounded readiness/retry | Improved in HDM | Typed stages, bounded timeouts, revalidation, single-owner workflows, and deterministic failure injection. Runtime/hardware retry claims remain evidence-gated. |
| Failure handling and rollback | Improved in HDM | Durable transaction journal, rollback contract, recovery explanations, and fail-closed unknown state. Native hardware recovery still needs scenario-specific proof. |
| Hot-plug observation | Missing / candidate | Topology events and attach readiness are read-only classifiers. No persistent automatic docking coordinator is authorized. |
| Missing-eGPU startup failback | Preserved, proof pending | Wrapper and recovery policy prefer a verified internal state; current HDM mechanism requires native hardware validation. |
| Disconnect readiness | Improved in HDM | Exact bounded client/storage/topology evidence and approval-bound process release. It never converts readiness into a live-unplug claim. |
| Physical PCI/USB4 live removal | Intentionally different / unsupported | Disabled for the certified G1 because eGPUBridge evidence included AMDGPU teardown stalls. Current policy is shutdown before disconnect. |
| Sleep/resume handling | Improved contract, incomplete proof | Login1 inhibitor, Steam preflight, wake/recovery policy, and evidence records exist. Final visible warning and scenario proofs remain. |
| Status/history/diagnostics | Improved in HDM | Privacy-safe versioned snapshot, health, stage timings, bounded actions, support preview/export, and build label. One packaged unified CLI/service/transaction report remains missing. |
| Link-health diagnostics | Preserved | Read-only exact-bridge link state is categorical and does not imply transition readiness by itself. |
| Controller/audio handoff | Missing / candidate | Pure contracts and read-only observations exist; no general hardware-tested handoff claim. |
| TV ADB/Wake-on-LAN/input control | Missing / candidate | Optional later adapter; not required for correct placement and not part of current authority. |
| Recovery hardware hotkeys | Missing / candidate | Deferred until the transition engine and native recovery are proven. |
| GPU telemetry | Intentionally different | Only bounded optional health/performance assessment contracts are considered; no broad telemetry/tuning surface. |
| GPU power/fan/clock/voltage tuning | Not applicable | Out of current product scope; would require separate profiles, bounds, watchdog, and rollback. |
| NVIDIA driver installation/removal | Not applicable | OS package/driver mutation is outside the Decky RPC surface. |
| TV/network launcher utilities | Not applicable | eGPUBridge convenience surfaces are not inherited into core HDM. |

## Proven lessons retained

The frozen eGPUBridge reference demonstrated these important facts on the first
hardware profile:

- connector presence is not active output; live Gamescope must agree
- both Gamescope output selection and Vulkan GPU selection matter
- card numbers, connector suffixes, and PCI addresses must be rediscovered
- running/unknown game state must block restart
- internal restore should be idempotent
- readiness must be bounded and verified after a new Gamescope process appears
- failure must preserve or restore the internal panel
- physical live G1 removal is not safe merely because software clients cleared

HDM carries those lessons through typed observations, profiles, policy, ports,
transactions, and native Decky presentation. It must not copy eGPUBridge's
monolith, broad root surface, hard-coded paths, tuning controls, or subjective UI.

## UX translation

Useful eGPUBridge UI characteristics are explicit in [UI specification](UI_SPEC.md):
one obvious primary action, adjacent status, visible restore/recovery, diagnostics
behind progressive disclosure, native controller controls, and clear errors.
HDM intentionally adds independent placement/health/workflow/confidence axes and
removes controls it cannot safely support.

## Review rule

Update this ledger whenever HDM changes a user-visible eGPU workflow, safety
gate, recovery path, diagnostic surface, or hardware evidence level. A row may
move to Preserved or Improved only when current HDM evidence supports the claim.
