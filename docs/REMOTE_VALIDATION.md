# Remote read-only validation

The maintainer may capture bounded Ally state over SSH without installing a
remote agent, opening a listener, or writing a file on the handheld.

## Command

From the repository on the development computer:

```text
python scripts/remote_capture.py --host <ally-ip> --identity-file <ssh-key>
```

The wrapper validates the destination, invokes OpenSSH without a shell, and
streams the fixed `remote_capture_payload.py` source to the Ally's `python3 -`
stdin. The payload imports HDM's installed read-only diagnostics, builds the same
bounded redacted support representation, and returns one JSON object on stdout.
It creates, edits, or removes no remote file.

The local result is created exclusively under `out/remote-captures/` by default.
Existing files are never overwritten. The report includes:

- collector source SHA-256 and no-write declaration
- hashed boot identity and bounded uptime
- categorical Steam/Gamescope/Decky process health counts without PIDs
- installed HDM version and hashes of fixed critical plugin files
- redacted HDM profile, GPU/display, game, blocker, and disconnect observations
- categorical collection errors

The report excludes hostnames, usernames, network addresses, PIDs, command
lines, environment values, raw hardware identifiers, and private paths.

## Important limitation

The streamed collector is not the live Decky plugin process. It therefore does
not own or observe the Decky-managed login1 sleep-inhibitor lease. The output
sets `sleep_guard.active` to `null`, gives the check result `not_observed`, and
records `plugin_lifecycle_sleep_guard_not_observed` as a limitation. Never use a
remote capture to claim the sleep guard is active or inactive.

An unprivileged SSH session may also be unable to read Gamescope's protected
environment. That is reported as incomplete evidence and remains fail closed.

## Allowed use

- package and installed-file provenance
- read-only before/live/after snapshots
- game-state and disconnect-blocker investigation
- simulator/result retrieval
- deciding whether a supervised test is ready to begin

## Prohibited use

The harness has no command for suspend, reboot, service restart, process signal,
display/GPU/controller/audio mutation, USB4 reset, or eGPU removal. Do not extend
it with arbitrary remote commands, paths, PIDs, or shell fragments. Any action
that may remove SSH, networking, or visible control belongs to the supervised
D6 stage in [Deployment and validation strategy](DEPLOYMENT_VALIDATION.md).

