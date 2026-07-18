"""Repository scan orchestration."""

from __future__ import annotations

import ast
from pathlib import Path

from archagent_audit import __version__
from archagent_audit.adapters.python import extract_python_evidence
from archagent_audit.config import discover_python_files, load_config
from archagent_audit.models import (
    AnalysisWarning,
    Coverage,
    Report,
    SEVERITY_ORDER,
)
from archagent_audit.redaction import redact_text
from archagent_audit.rules.aa001 import evaluate_aa001


def _is_suppressed(lines: list[str], line: int, rule_id: str) -> bool:
    directive = f"# archagent-audit: ignore {rule_id}"
    indexes = [line - 1, line - 2]
    return any(0 <= index < len(lines) and directive in lines[index] for index in indexes)


def _excerpt(lines: list[str], line: int) -> str:
    start = max(0, line - 2)
    end = min(len(lines), line + 1)
    return "\n".join(lines[start:end])


def scan_path(root: str | Path) -> Report:
    scan_root = Path(root).resolve()
    if not scan_root.exists() or not scan_root.is_dir():
        raise ValueError(f"Scan path is not a directory: {scan_root}")
    config = load_config(scan_root)
    files, skipped = discover_python_files(scan_root, config)
    report = Report(
        tool_version=__version__,
        scan_root=str(scan_root),
        coverage=Coverage(files_discovered=len(files), files_skipped=skipped),
    )
    frameworks: set[str] = set()
    for path in files:
        relative = path.relative_to(scan_root).as_posix()
        try:
            source = path.read_text(encoding="utf-8")
            evidence = extract_python_evidence(source)
        except (UnicodeDecodeError, SyntaxError) as error:
            line = error.lineno if isinstance(error, SyntaxError) else None
            report.analysis_warnings.append(
                AnalysisWarning(
                    code="PYTHON_PARSE_ERROR",
                    message="Python source could not be parsed.",
                    file=relative,
                    line=line,
                )
            )
            continue
        report.coverage.files_analyzed += 1
        frameworks.update(evidence.frameworks)
        lines = source.splitlines()
        for loop in evidence.loops:
            if _is_suppressed(lines, loop.line, "AA001"):
                report.suppressions += 1
                continue
            excerpt, counts = redact_text(_excerpt(lines, loop.line))
            report.redactions.add(counts)
            finding, warning = evaluate_aa001(
                loop,
                file=relative,
                excerpt=excerpt,
            )
            if finding:
                report.findings.append(finding)
            if warning:
                report.analysis_warnings.append(warning)
    report.coverage.frameworks_detected = sorted(frameworks)
    report.coverage.rules_evaluated = ["AA001"] if files else []
    report.findings.sort(
        key=lambda item: (
            SEVERITY_ORDER[item.severity],
            item.file,
            item.line,
            item.rule_id,
        )
    )
    report.analysis_warnings.sort(
        key=lambda item: (item.file or "", item.line or 0, item.code)
    )
    return report

