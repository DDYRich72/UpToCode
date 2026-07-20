"""Human-readable terminal reporting."""

from __future__ import annotations

from uptocode.models import Report


def render_terminal(report: Report) -> str:
    lines = [
        "UpToCode scan",
        f"Coverage: {report.coverage.files_analyzed}/{report.coverage.files_discovered} files analyzed",
        f"Findings: {len(report.findings)} | Warnings: {len(report.analysis_warnings)} | Redactions: {report.redactions.secrets + report.redactions.pii}",
        f"Experimental rules evaluated: {len(report.coverage.experimental_rules_evaluated)}",
    ]
    if report.baseline_debt.new or report.baseline_debt.aging or report.baseline_debt.resolved:
        lines.append(
            "Baseline debt: "
            f"{len(report.baseline_debt.new)} new | "
            f"{len(report.baseline_debt.aging)} aging | "
            f"{len(report.baseline_debt.resolved)} resolved"
        )
    for finding in report.findings:
        lines.append(
            f"[{finding.severity.value.upper()}] {finding.rule_id}"
            f"{' [EXPERIMENTAL]' if finding.maturity == 'experimental' else ''} "
            f"{finding.file}:{finding.line} - {finding.title}"
        )
    for warning in report.analysis_warnings:
        location = f" {warning.file}:{warning.line}" if warning.file else ""
        lines.append(f"[ANALYSIS] {warning.code}{location} - {warning.message}")
    return "\n".join(lines)
