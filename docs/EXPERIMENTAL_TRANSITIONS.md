# Guarded experimental transitions

Hardware validation is a certification gate, not an implementation gate. HDM
may implement an Experimental mechanism before certification when the operation
is exact, observable, bounded, recoverable, and explicitly approved for a
supervised test.

## Runtime profile resolution

The runtime registry resolves capabilities from the complete current snapshot.
It selects the Ally X host profile only from the exact host profile ID and the
GPD G1 profile only when one verified external GPU has the stable identity that
the exact G1 matcher assigned and the complete combination remains Certified.
Unknown or ambiguous evidence receives the unknown profile and no mutation
right. Resolution does not change Experimental capabilities to Verified.

The manual planner derives an ephemeral transition binding containing the exact
host/eGPU profiles and current internal/external GPU and display stable IDs.
This binding is needed by a mechanism but is excluded from the privacy-safe
transition journal and support exports. A mutating plan cannot exist without a
complete binding.

## Experimental approval

Verified capabilities need no experimental exception. An Experimental display
handoff requires a separate backend-issued permit that is:

- based on explicit user confirmation
- valid for at most two minutes
- single use
- bound to the operation, observation generation, target placement, host
  profile, eGPU profile, and ephemeral eGPU identity

The planner rejects a missing, stale, or differently bound permit. This is not
a general `allow_experimental` frontend boolean. No public RPC or automatic
attach path can currently issue or consume the permit.

## Certification boundary

An approved Experimental plan authorizes one controlled attempt after the
runtime orchestrator and mechanism are available. It does not mark the result
Verified or Certified. Promotion still requires the intentional hardware
review rules in [Hardware support](HARDWARE_SUPPORT.md) and a captured
before/attempt/verification/rollback record.
