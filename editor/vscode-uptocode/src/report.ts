export type Severity = "critical" | "warning" | "info";

export interface Citation {
  url: string;
}

export interface Finding {
  rule_id: string;
  severity: Severity;
  title: string;
  file: string;
  line: number;
  maturity?: "stable" | "experimental";
  citations?: Citation[];
  verdict?: { observed?: string };
}

export interface AnalysisWarning {
  code: string;
  message: string;
  file?: string;
  line?: number;
}

export interface Report {
  findings: Finding[];
  analysis_warnings: AnalysisWarning[];
}

export interface MappedDiagnostic {
  line: number;
  severity: Severity;
  code: string;
  href?: string;
  message: string;
}

export function parseReport(value: string): Report {
  const parsed: unknown = JSON.parse(value);
  if (typeof parsed !== "object" || parsed === null) throw new Error("report is not an object");
  const candidate = parsed as Partial<Report>;
  if (!Array.isArray(candidate.findings) || !Array.isArray(candidate.analysis_warnings)) {
    throw new Error("report is missing findings or analysis_warnings");
  }
  return candidate as Report;
}

export function mapFindings(report: Report): MappedDiagnostic[] {
  return report.findings.map((finding) => {
    const observed = finding.verdict?.observed?.trim();
    const experimental = finding.maturity === "experimental" ? " [experimental]" : "";
    return {
      line: Math.max(1, finding.line),
      severity: finding.severity,
      code: finding.rule_id,
      href: finding.citations?.[0]?.url,
      message: `${finding.title}${experimental}${observed ? ` — ${observed}` : ""}`,
    };
  });
}
