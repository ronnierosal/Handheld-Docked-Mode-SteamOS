import deckyPlugin from "@decky/rollup";

const config = deckyPlugin({});
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
