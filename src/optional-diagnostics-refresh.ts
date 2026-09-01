import type {
  ActionHistoryPayload,
  DiagnosticLoggingStatusPayload,
  DockedIgpuStatusPayload,
  PeripheralStatusPayload,
} from "./backend";


export interface OptionalDiagnosticValues {
  dockedIgpuStatus: DockedIgpuStatusPayload | null;
  diagnosticLoggingStatus: DiagnosticLoggingStatusPayload | null;
  peripheralStatus: PeripheralStatusPayload | null;
  actionHistory: ActionHistoryPayload | null;
}

export interface OptionalDiagnosticSources {
  getDockedIgpuStatus: () => Promise<DockedIgpuStatusPayload>;
  getDiagnosticLoggingStatus: () => Promise<DiagnosticLoggingStatusPayload>;
  getPeripheralStatus: () => Promise<PeripheralStatusPayload>;
  getActionHistory: () => Promise<ActionHistoryPayload>;
}

const EMPTY_VALUES: OptionalDiagnosticValues = {
  dockedIgpuStatus: null,
  diagnosticLoggingStatus: null,
  peripheralStatus: null,
  actionHistory: null,
};

function optionalCall<T>(source: () => Promise<T>): Promise<T | null> {
  return Promise.resolve().then(source).catch(() => null);
}

export async function collectOptionalDiagnostics(
  visible: boolean,
  sources: OptionalDiagnosticSources,
): Promise<OptionalDiagnosticValues> {
  if (!visible) {
    return EMPTY_VALUES;
  }
  const [dockedIgpuStatus, diagnosticLoggingStatus, peripheralStatus, actionHistory] = await Promise.all([
    optionalCall(sources.getDockedIgpuStatus),
    optionalCall(sources.getDiagnosticLoggingStatus),
    optionalCall(sources.getPeripheralStatus),
    optionalCall(sources.getActionHistory),
  ]);
  return {
    dockedIgpuStatus,
    diagnosticLoggingStatus,
    peripheralStatus,
    actionHistory,
  };
}
