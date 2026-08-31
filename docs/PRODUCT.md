# Product definition

## Objective

HDM provides a console-like docking experience for SteamOS handheld PCs. It
detects current hardware and gaming state, explains the safest available action,
and eventually performs verified, recoverable transitions without requiring the
player to understand Linux display or GPU internals.

## Target user-facing placement

- **Portable:** internal GPU renders to the internal panel.
- **Boosted Handheld:** a verified eGPU renders to the internal panel.
- **Docked-iGPU:** the current game remains on the internal GPU while its
  presentation is verified on the external display.
- **Docked-eGPU:** a verified eGPU renders to its directly attached external
  display.

These labels are derived only from independently observed render-GPU and display
state. Incomplete or conflicting evidence is reported as Unknown or Degraded.
The current executable `TV Docked` label corresponds only to the target
Docked-eGPU placement. Docked-iGPU is research, not an implemented claim.

Connecting, Preparing to disconnect, Safe to disconnect, Returning to portable,
Sleep pending disconnect, Action required, and Failure are workflow phases, not
placement modes. HDM keeps both dimensions visible internally so a pending or
failed operation cannot overwrite observed hardware truth.

## Product behavior

Every future transition follows:

```text
DETECT → VALIDATE → PLAN → PREPARE → APPLY → VERIFY → COMMIT
                                      │
                                      └─ failure → ROLL BACK or retain known-good state
```

Manual and automatic requests use the same policy and transition engine.

## Decky-native delivery

HDM is a Decky Loader-native plugin. Its player interface uses Decky's Quick
Access components and typed Decky RPC. The Python backend runs under Decky's
managed plugin lifecycle; there is no separate web dashboard or general-purpose
command endpoint. Root privilege is isolated to narrow observation and future
approved mechanisms, while policy remains pure and testable.

## Initial scope

The first certified profile is:

- ASUS ROG Ally X
- SteamOS
- GPD G1 with AMD Radeon RX 7600M XT
- TV connected through the G1 display output

Milestone 0.1 implements reliable read-only discovery and diagnostics. The first
approved 0.2 mechanism is a reversible login1 sleep-inhibitor lease for the G1;
display/GPU transitions and process signals remain unimplemented.

The proposed eGPUBridge-derived feature selection, including sleep blocking and
guarded process closure, is documented in
[eGPUBridge feature review for HDM](EGPUBRIDGE_FEATURE_REVIEW.md). These are 0.2
candidates. The sleep guard is now explicitly in 0.2 scope; the other mutation
boundaries remain closed until their own design and validation gates pass.
The complementary [Steam sleep preflight](ADR_STEAM_SLEEP_PREFLIGHT.md) is now
implemented and has passed its non-sleep lease-lifecycle proof. Sleep protection
is not considered complete until its supervised request proof also passes.
Read-only responsiveness instrumentation, adaptive Decky refresh, progressive
connection states, and the [privacy-safe support bundle](SUPPORT_BUNDLE.md) are
also implemented in 0.2. They do not authorize display/GPU mutation, process
signals, or live hardware removal.

The reconciled product ordering and evidence status are maintained in the
[authoritative roadmap](ROADMAP.md). Its staged
[deployment and validation strategy](DEPLOYMENT_VALIDATION.md) is a release
gate for hardware-facing work.

## Non-goals for the initial release

- Windows support
- Every handheld or eGPU
- Physical live eGPU removal
- Running-workload GPU migration
- Arbitrary desktop Linux distributions
- GPU tuning, fan control, overclocking, or driver installation
- TV network automation, cloud services, or a general plugin ecosystem
