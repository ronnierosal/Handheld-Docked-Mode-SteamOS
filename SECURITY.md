# Security policy

HDM is in active development and has no supported public end-user release yet.

## Reporting a vulnerability

Please use GitHub's private security advisory flow for this repository. Do not
open a public issue for a vulnerability that exposes credentials, private device
identity, arbitrary root command execution, unsafe hardware mutation, support
bundle disclosure, or a reliable denial of recovery.

Include the affected revision/version, impact, minimal reproduction, and whether
the issue requires a particular hardware profile. Remove hostnames, addresses,
usernames, paths, raw hardware identifiers, tokens, keys, and personal data.

## Security boundaries

- The Decky backend is root privileged; its public RPC surface is allowlisted
  and must not become a general command endpoint.
- Diagnostics and support exports are bounded, redacted, local-first, and
  previewed before an approved write.
- Support submission remains dormant; no endpoint, cloud resource, credential,
  or silent upload is configured.
- Deployment accepts one provenance-checked package through documented,
  maintainer-authorized paths. It does not authorize display, GPU, sleep,
  controller, audio, or physical eGPU actions.
- Unknown identity, game state, readiness, or rollback evidence fails closed.

Do not commit `.env` files, private keys, signing certificates, credentials,
device addresses, or raw support data. See [Diagnostics](docs/DIAGNOSTICS.md),
[Support bundle](docs/SUPPORT_BUNDLE.md), and
[Deployment validation](docs/DEPLOYMENT_VALIDATION.md).
