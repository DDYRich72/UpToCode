"""GitHub workflow annotations and job-summary rendering."""

from __future__ import annotations

from collections import Counter

from uptocode.models import Report, Severity


MAX_SUMMARY_FINDINGS = 20
MAX_SUMMARY_WARNINGS = 10

_COMMAND = {
    Severity.CRITICAL: "error",
    Severity.WARNING: "warning",
    Severity.INFO: "notice",
}


def escape_command_data(value: str) -> str:
    """Escape untrusted workflow-command message data in GitHub's required order."""
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def escape_command_property(value: str) -> str:
    """Escape untrusted workflow-command property data."""
    return escape_command_data(value).replace(":", "%3A").replace(",", "%2C")


def render_github(report: Report) -> str:
    """Render findings as injection-safe GitHub workflow commands."""
    lines = []
    for finding in report.findings:
        properties = (
            f"file={escape_command_property(finding.file)},"
            f"line={finding.line},"
            f"title={escape_command_property(finding.rule_id)}"
        )
        lines.append(
            f"::{_COMMAND[finding.severity]} {properties}::"
            f"{escape_command_data(finding.verdict.observed)}"
        )
    return "\n".join(lines)


def _markdown_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def render_github_summary(report: Report) -> str:
    """Render a bounded Markdown summary suitable for ``GITHUB_STEP_SUMMARY``."""
    totals = Counter(finding.severity for finding in report.findings)
    discovered = report.coverage.files_discovered
    analyzed = report.coverage.files_analyzed
    percentage = round((analyzed / discovered) * 100) if discovered else 100
    lines = [
        "# UpToCode scan summary",
        "",
        f"- Coverage: **{analyzed}/{discovered} files ({percentage}%)**",
        f"- Analysis warnings: **{len(report.analysis_warnings)}**",
        f"- Suppressions: **{report.suppressions}**",
        "",
        "| Severity | Findings |",
        "|---|---:|",
        f"| Critical | {totals[Severity.CRITICAL]} |",
        f"| Warning | {totals[Severity.WARNING]} |",
        f"| Info | {totals[Severity.INFO]} |",
        "",
        f"## Top findings (up to {MAX_SUMMARY_FINDINGS})",
        "",
    ]
    if report.findings:
        lines.extend(
            [
                "| Severity | Rule | Location | Observed |",
                "|---|---|---|---|",
            ]
        )
        for finding in report.findings[:MAX_SUMMARY_FINDINGS]:
            location = f"{finding.file}:{finding.line}"
            lines.append(
                f"| {_markdown_cell(finding.severity.value)} "
                f"| {_markdown_cell(finding.rule_id)} "
                f"| {_markdown_cell(location)} "
                f"| {_markdown_cell(finding.verdict.observed)} |"
            )
        remaining = len(report.findings) - MAX_SUMMARY_FINDINGS
        if remaining > 0:
            lines.extend(["", f"_{remaining} additional findings omitted._"])
    else:
        lines.append("No findings.")

    if report.analysis_warnings:
        lines.extend(["", f"## Analysis warnings (up to {MAX_SUMMARY_WARNINGS})", ""])
        for warning in report.analysis_warnings[:MAX_SUMMARY_WARNINGS]:
            location = f" ({warning.file}:{warning.line})" if warning.file else ""
            lines.append(
                f"- `{_markdown_cell(warning.code)}`{_markdown_cell(location)}: "
                f"{_markdown_cell(warning.message)}"
            )
        remaining = len(report.analysis_warnings) - MAX_SUMMARY_WARNINGS
        if remaining > 0:
            lines.append(f"- _{remaining} additional warnings omitted._")

    return "\n".join(lines) + "\n"
