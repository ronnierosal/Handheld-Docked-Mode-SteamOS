import deckyPlugin from "@decky/rollup";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const config = deckyPlugin({});
// Bundle the approved artwork locally; no network or plugin-path dependency.
const brandImagePath = fileURLToPath(new URL("./docs/images/re-gear-icon.png", import.meta.url));
config.plugins.push({
  name: "re-gear-brand-image",
  load(id) {
    if (id !== brandImagePath) return null;
    return `export default ${JSON.stringify("data:image/png;base64," + readFileSync(brandImagePath).toString("base64"))};`;
  },
});
const deckySourcemapPathTransform = config.output.sourcemapPathTransform;

// @decky/rollup expects POSIX separators when it rewrites source paths to
// decky:// URLs. Rollup supplies native backslashes on Windows, which made the
// committed source map differ from the one rebuilt by Linux CI.
config.output.sourcemapPathTransform = (relativeSourcePath, sourcemapPath) =>
  deckySourcemapPathTransform(
    relativeSourcePath.replaceAll("\\", "/"),
    sourcemapPath,
  );

export default config;
