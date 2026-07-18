"""Human-readable terminal reporting."""

from __future__ import annotations

from archagent_audit.models import Report


def render_terminal(report: Report) -> str:
    lines = [
        "ArchAgent scan",
        f"Coverage: {report.coverage.files_analyzed}/{report.coverage.files_discovered} files analyzed",
        f"Findings: {len(report.findings)} | Warnings: {len(report.analysis_warnings)} | Redactions: {report.redactions.secrets}",
    ]
    for finding in report.findings:
        lines.append(
            f"[{finding.severity.value.upper()}] {finding.rule_id} {finding.file}:{finding.line} — {finding.title}"
        )
    for warning in report.analysis_warnings:
        location = f" {warning.file}:{warning.line}" if warning.file else ""
        lines.append(f"[ANALYSIS] {warning.code}{location} — {warning.message}")
    return "\n".join(lines)

