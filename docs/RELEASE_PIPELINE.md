# Release-candidate pipeline

HDM has a local, publish-ready candidate contract, not an automated release
channel. `package.json` is the semantic-version source. The pipeline rejects a
non-semantic version, a mismatched Python package version, a ZIP whose filename
or embedded package/build metadata disagree, or an invalid source revision.

From a clean validated checkout:

```text
pnpm build
python scripts/check_plugin_package.py .
python scripts/build_plugin.py
python scripts/prepare_release_candidate.py out/HandheldDockMode-<version>.zip \
  --output out/release-candidate.json \
  --notes-template out/RELEASE_NOTES_TEMPLATE.md
```

The generated JSON records the exact version, full build revision, archive
filename, SHA-256, required release-note fields, and explicit non-publication
status. The Markdown template is the maintainer's starting point for player
changes, known limits, validation evidence, and the final manual publication
record. It contains no device identifier, credential, or secret.

CI repeats this local verification and retains the ZIP, checksum, candidate
manifest, and notes template as a short-lived controlled validation artifact.
It has read-only repository permissions and does not publish a GitHub Release,
contact Decky, register a store channel, deploy, or use publication secrets.

## Manual publication gate

Only after a maintainer has reviewed the candidate, completed the applicable
hardware/certification gates, and finalized release notes may they manually:

1. Create a GitHub Release and attach the exact verified ZIP and SHA-256.
2. Record the Release URL and evidence status in the finalized notes.
3. Complete Decky Store/channel registration and its separate review process.

Decky Store/channel registration is not implemented by this repository or CI.
Until it is explicitly completed, every candidate remains a controlled
validation artifact and not an end-user release.
