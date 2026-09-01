import assert from "node:assert/strict";
import test from "node:test";

import {
  collectOptionalDiagnostics,
  shouldCollectOptionalDiagnostics,
} from "../src/optional-diagnostics-refresh.ts";


function sources() {
  const calls = [];
  const source = (name) => async () => {
    calls.push(name);
    return { name };
  };
  return {
    calls,
    values: {
      getDockedIgpuStatus: source("docked"),
      getDiagnosticLoggingStatus: source("logging"),
      getPeripheralStatus: source("peripheral"),
      getActionHistory: source("history"),
    },
  };
}

test("hidden troubleshooting makes no optional diagnostic requests", async () => {
  const fixture = sources();
  const result = await collectOptionalDiagnostics(false, fixture.values);
  assert.deepEqual(fixture.calls, []);
  assert.deepEqual(result, {
    dockedIgpuStatus: null,
    diagnosticLoggingStatus: null,
    peripheralStatus: null,
    actionHistory: null,
  });
});

test("optional diagnostics defer until exact idle game evidence", () => {
  assert.equal(shouldCollectOptionalDiagnostics(false, "idle"), false);
  assert.equal(shouldCollectOptionalDiagnostics(true, "running"), false);
  assert.equal(shouldCollectOptionalDiagnostics(true, "unknown"), false);
  assert.equal(shouldCollectOptionalDiagnostics(true, undefined), false);
  assert.equal(shouldCollectOptionalDiagnostics(true, "idle"), true);
});

test("visible troubleshooting requests each optional status once", async () => {
  const fixture = sources();
  const result = await collectOptionalDiagnostics(true, fixture.values);
  assert.deepEqual(fixture.calls.sort(), ["docked", "history", "logging", "peripheral"]);
  assert.equal(result.peripheralStatus.name, "peripheral");
  assert.equal(result.actionHistory.name, "history");
});

test("an optional synchronous failure cannot interrupt the remaining diagnostics", async () => {
  const fixture = sources();
  fixture.values.getPeripheralStatus = () => {
    throw new Error("unavailable");
  };
  const result = await collectOptionalDiagnostics(true, fixture.values);
  assert.equal(result.peripheralStatus, null);
  assert.equal(result.dockedIgpuStatus.name, "docked");
  assert.equal(result.actionHistory.name, "history");
});
