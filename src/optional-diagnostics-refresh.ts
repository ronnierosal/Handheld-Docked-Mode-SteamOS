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

export async function collectOptionalDiagnostics(
  visible: boolean,
  sources: OptionalDiagnosticSources,
): Promise<OptionalDiagnosticValues> {
  if (!visible) {
    return EMPTY_VALUES;
  }
  const [dockedIgpuStatus, diagnosticLoggingStatus, peripheralStatus, actionHistory] = await Promise.all([
    sources.getDockedIgpuStatus().catch(() => null),
    sources.getDiagnosticLoggingStatus().catch(() => null),
    sources.getPeripheralStatus().catch(() => null),
    sources.getActionHistory().catch(() => null),
  ]);
  return {
    dockedIgpuStatus,
    diagnosticLoggingStatus,
    peripheralStatus,
    actionHistory,
  };
}
