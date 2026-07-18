"""Repository scan orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from archagent_audit import __version__
from archagent_audit.analysis import FileFacts, analyze_source
from archagent_audit.adapters.python import extract_python_evidence
from archagent_audit.config import discover_python_files, load_config
from archagent_audit.judgment import run_judgment
from archagent_audit.judgment_candidates import collect_judgment_candidates
from archagent_audit.models import (
    AnalysisWarning,
    Coverage,
    Report,
    SEVERITY_ORDER,
)
from archagent_audit.redaction import redact_text
from archagent_audit.rules.aa001 import evaluate_aa001
from archagent_audit.rules.static import evaluate_file, evaluate_project


def _is_suppressed(lines: list[str], line: int, rule_id: str) -> bool:
    directive = f"# archagent-audit: ignore {rule_id}"
    indexes = [line - 1, line - 2]
    return any(0 <= index < len(lines) and directive in lines[index] for index in indexes)


def _excerpt(lines: list[str], line: int) -> str:
    start = max(0, line - 2)
    end = min(len(lines), line + 1)
    return "\n".join(lines[start:end])


def scan_path(
    root: str | Path,
    *,
    judgment: bool = False,
    send_code: bool = False,
    judgment_client: Any | None = None,
) -> Report:
    if judgment and not send_code:
        raise ValueError("Judgment requires explicit --send-code authorization.")
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
    project_facts: list[tuple[str, list[str], FileFacts]] = []
    judgment_sources: list[tuple[str, str]] = []
    for path in files:
        relative = path.relative_to(scan_root).as_posix()
        try:
            source = path.read_text(encoding="utf-8")
            evidence = extract_python_evidence(source)
            import ast

            facts = analyze_source(ast.parse(source), source)
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
        judgment_sources.append((relative, source))
        frameworks.update(evidence.frameworks)
        lines = source.splitlines()
        project_facts.append((relative, lines, facts))
        for loop in evidence.loops:
            if _is_suppressed(lines, loop.line, "AA001"):
                report.suppressions += 1
                continue
            excerpt = _excerpt(lines, loop.line)
            finding, warning = evaluate_aa001(
                loop,
                file=relative,
                excerpt=excerpt,
            )
            if finding:
                report.findings.append(finding)
            if warning:
                report.analysis_warnings.append(warning)
        report.findings.extend(evaluate_file(relative, lines, facts))
    report.findings.extend(evaluate_project(project_facts))
    filtered_findings = []
    for finding in report.findings:
        source_lines = next((lines for file, lines, _ in project_facts if file == finding.file), [])
        if _is_suppressed(source_lines, finding.line, finding.rule_id):
            report.suppressions += 1
            continue
        finding.excerpt, counts = redact_text(finding.excerpt)
        report.redactions.add(counts)
        filtered_findings.append(finding)
    report.findings = filtered_findings
    report.coverage.frameworks_detected = sorted(frameworks)
    if project_facts and any(facts.agent_present or facts.model_calls for _, _, facts in project_facts):
        report.coverage.rules_evaluated = [
            "AA001", "AA002", "AA003", "AA004", "AA006", "AA007", "AA010", "AA011", "AA012"
        ]
        report.coverage.rules_not_applicable = ["AA005", "AA008", "AA009"]
    elif files:
        report.coverage.rules_not_applicable = [f"AA{index:03d}" for index in range(1, 13)]
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
    if judgment:
        candidates = collect_judgment_candidates(judgment_sources)
        if judgment_client is None:
            try:
                from openai import OpenAI

                judgment_client = OpenAI(max_retries=2, timeout=30.0)
            except Exception:
                report.judgment_status = "failed"
                report.analysis_warnings.append(
                    AnalysisWarning(
                        code="JUDGMENT_CREDENTIALS_UNAVAILABLE",
                        message=(
                            "Judgment credentials are unavailable; static results were preserved."
                        ),
                    )
                )
                return report
        run_judgment(report, candidates, client=judgment_client)
    return report
