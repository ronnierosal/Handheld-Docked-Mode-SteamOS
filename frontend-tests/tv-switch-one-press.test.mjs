import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";

const source = readFileSync(new URL("../src/index.tsx", import.meta.url), "utf8");

test("TV switching has one visible activation control", () => {
  assert.match(source, /onClick=\{\(\) => void executeTvSwitch\(\)\}/);
  assert.doesNotMatch(source, /showSupervisedTvSwitchConfirmation/);
  assert.doesNotMatch(source, /previewSupervisedTvSwitch/);
});
