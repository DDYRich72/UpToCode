import { mapFindings, type MappedDiagnostic } from "./report.js";
import type { ScanOutcome } from "./scanner.js";

export interface DiagnosticUpdate {
  diagnostics: MappedDiagnostic[];
  messages: string[];
}

export function toDiagnosticUpdate(outcome: ScanOutcome): DiagnosticUpdate {
  if (!outcome.report) {
    return {
      diagnostics: [],
      messages: [outcome.error ?? "scan failed", outcome.stderr.trim()].filter(Boolean),
    };
  }
  return {
    diagnostics: mapFindings(outcome.report),
    messages: outcome.report.analysis_warnings.map((warning) => {
      const location = warning.file
        ? `${warning.file}${warning.line ? `:${warning.line}` : ""}: `
        : "";
      return `${location}${warning.code}: ${warning.message}`;
    }),
  };
}
