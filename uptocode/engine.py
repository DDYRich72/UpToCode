"""Repository scan orchestration."""

from __future__ import annotations

import ast
import json
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from uptocode import __version__
from uptocode.analysis import FileFacts, analyze_source, qualified_name
from uptocode.adapters.python import extract_python_evidence
from uptocode.config import RuleOverride, discover_python_files_detailed, load_config
from uptocode.fingerprints import content_fingerprint
from uptocode.judgment import run_judgment
from uptocode.judgment_candidates import collect_judgment_candidates
from uptocode.models import (
    AnalysisWarning,
    Coverage,
    Report,
    RuleResult,
    RuleStatus,
    ScanMetadata,
    SEVERITY_ORDER,
    Severity,
    SkippedFile,
)
from uptocode.redaction import redact_text
from uptocode.rules.aa001 import evaluate_aa001
from uptocode.rules.registry import load_core_rules
from uptocode.rules.plugins import (
    NormalizedFileEvidence,
    RuleContext,
    evaluate_plugins,
    load_rule_plugins,
)
from uptocode.rules.static import evaluate_file, evaluate_project
from uptocode.suppressions import SuppressionIndex, parse_suppressions


def _excerpt(lines: list[str], line: int) -> str:
    start = max(0, line - 2)
    end = min(len(lines), line + 1)
    return "\n".join(lines[start:end])


def _repository_revision(root: Path) -> str | None:
    if not (root / ".git").exists():
        return None
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def _rule_results(report: Report, *, judgment_requested: bool) -> list[RuleResult]:
    definitions = load_core_rules()
    findings = {definition.id: 0 for definition in definitions}
    for finding in report.findings:
        findings[finding.rule_id] = findings.get(finding.rule_id, 0) + 1
    warnings_by_rule = {
        warning.code[:5]
        for warning in report.analysis_warnings
        if warning.code.startswith("AA") and len(warning.code) >= 5
    }
    judgment_rules = {definition.id for definition in definitions if definition.tier == "judgment"}
    results: list[RuleResult] = []
    for rule_id in sorted(findings):
        count = findings[rule_id]
        status: RuleStatus
        if count:
            status = "finding"
        elif rule_id in warnings_by_rule:
            status = "inconclusive"
        elif rule_id in judgment_rules and not judgment_requested:
            status = "not_requested"
        elif rule_id in report.coverage.rules_not_applicable:
            status = "not_applicable"
        else:
            status = "passed"
        results.append(RuleResult(rule_id=rule_id, status=status, finding_count=count))
    return results


def _scan_path_impl(
    root: str | Path,
    *,
    judgment: bool = False,
    send_code: bool = False,
    judgment_client: Any | None = None,
    extra_excludes: list[str] | None = None,
    severity_overrides: dict[str, str] | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> Report:
    if judgment and not send_code:
        raise ValueError("Judgment requires explicit --send-code authorization.")
    started = time.monotonic()
    target = Path(root).resolve()
    if not target.exists() or (target.is_file() and target.suffix.lower() != ".py"):
        raise ValueError(f"Scan target must be a Python file or directory: {target}")
    scan_root = target.parent if target.is_file() else target
    config = load_config(scan_root)
    if extra_excludes:
        config = config.model_copy(update={"exclude": [*config.exclude, *extra_excludes]})
    if severity_overrides:
        rules = dict(config.rules)
        for rule_id, severity in severity_overrides.items():
            existing = rules.get(rule_id.upper(), RuleOverride())
            rules[rule_id.upper()] = RuleOverride(
                enabled=existing.enabled,
                severity=Severity(severity),
            )
        config = config.model_copy(update={"rules": rules})
    if target.is_file():
        try:
            size = target.stat().st_size
        except OSError as error:
            raise ValueError(f"Could not inspect scan file: {target}") from error
        if size > config.max_file_size:
            files: list[Path] = []
            skipped_details = [SkippedFile(path=target.name, reason="file-too-large")]
        else:
            files = [target]
            skipped_details = []
    else:
        files, skipped_details = discover_python_files_detailed(scan_root, config)
    report = Report(
        tool_version=__version__,
        scan_root=str(scan_root),
        coverage=Coverage(
            files_discovered=len(files),
            files_skipped=len(skipped_details),
            skipped_files=skipped_details,
        ),
    )
    frameworks: set[str] = set()
    definitions = load_core_rules()
    suppression_indexes: dict[str, SuppressionIndex] = {}
    counted_suppressions: set[tuple[str, int, str]] = set()

    def is_suppressed(file: str, line: int, rule_id: str) -> bool:
        directive = suppression_indexes.get(file, SuppressionIndex([])).find(rule_id, line)
        if directive is None or not directive.active:
            return False
        key = (file, directive.detail.line, rule_id)
        if key not in counted_suppressions:
            counted_suppressions.add(key)
            report.suppressions += 1
        return True
    project_facts: list[tuple[str, list[str], FileFacts]] = []
    judgment_sources: list[tuple[str, str]] = []
    normalized_files: list[NormalizedFileEvidence] = []
    total_source_size = 0
    for path in files:
        if cancelled is not None and cancelled():
            report.analysis_warnings.append(
                AnalysisWarning(
                    code="SCAN_CANCELLED",
                    message="The scan was cancelled; partial results were preserved.",
                )
            )
            break
        if time.monotonic() - started > config.deadline_seconds:
            report.analysis_warnings.append(
                AnalysisWarning(
                    code="SCAN_DEADLINE_EXCEEDED",
                    message="The scan deadline was reached; partial results were preserved.",
                )
            )
            break
        relative = path.relative_to(scan_root).as_posix()
        try:
            source = path.read_text(encoding="utf-8")
            total_source_size += len(source.encode("utf-8"))
            if total_source_size > config.max_total_source_size:
                report.coverage.files_skipped += 1
                report.coverage.skipped_files.append(
                    SkippedFile(path=relative, reason="aggregate-source-budget")
                )
                report.analysis_warnings.append(
                    AnalysisWarning(
                        code="SOURCE_BUDGET_EXCEEDED",
                        message="The aggregate source budget was reached; partial results were preserved.",
                        file=relative,
                    )
                )
                break
            evidence = extract_python_evidence(source)
            tree = ast.parse(source)
            facts = analyze_source(tree, source)
        except OSError:
            report.analysis_warnings.append(
                AnalysisWarning(
                    code="FILE_READ_ERROR",
                    message="Python source could not be read; remaining files were preserved.",
                    file=relative,
                )
            )
            continue
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
        if (
            ("tools=" in source or "tools =" in source or "@tool" in source)
            and "@function_tool" not in source
            and any(token in source for token in ("Agent", "graph", "langgraph"))
        ):
            report.analysis_warnings.append(
                AnalysisWarning(
                    code="UNSUPPORTED_TOOL_WIRING",
                    message=(
                        "Tool wiring is not a recognized OpenAI function_tool construct; "
                        "AA003, AA004, and AA009 coverage may be incomplete."
                    ),
                    file=relative,
                )
            )
        report.coverage.files_analyzed += 1
        judgment_sources.append((relative, source))
        has_agent_reference = any(
            isinstance(node, (ast.Name, ast.Attribute))
            and any(
                token in qualified_name(node)
                for token in ("Agent", "Runner", "responses", "function_tool", "graph")
            )
            for node in ast.walk(tree)
        )
        has_dynamic_dispatch = any(
            isinstance(node, ast.Call)
            and (
                (
                    qualified_name(node.func) in {"exec", "eval"}
                    and has_agent_reference
                )
                or (
                    qualified_name(node.func) in {"getattr", "setattr"}
                    and bool(node.args)
                    and any(
                        token in qualified_name(node.args[0])
                        for token in (
                            "Agent",
                            "Runner",
                            "responses",
                            "function_tool",
                            "graph",
                        )
                    )
                )
            )
            for node in ast.walk(tree)
        )
        if has_dynamic_dispatch and has_agent_reference:
            report.analysis_warnings.append(
                AnalysisWarning(
                    code="UNSUPPORTED_DYNAMIC_AGENT_SYNTAX",
                    message=(
                        "Dynamic agent construction or dispatch is outside static coverage; "
                        "applicable rule results may be incomplete."
                    ),
                    file=relative,
                )
            )
        frameworks.update(evidence.frameworks)
        lines = source.splitlines()
        suppression_index, suppression_warnings = parse_suppressions(lines, file=relative)
        suppression_indexes[relative] = suppression_index
        report.suppression_details.extend(item.detail for item in suppression_index.directives)
        report.analysis_warnings.extend(suppression_warnings)
        project_facts.append((relative, lines, facts))
        normalized_files.append(
            NormalizedFileEvidence(
                file=relative,
                frameworks=sorted(evidence.frameworks),
                agent_present=facts.agent_present,
                model_call_count=len(facts.model_calls),
                tool_count=len(facts.tools),
                loop_count=len(evidence.loops),
            )
        )
        for loop in evidence.loops:
            if is_suppressed(relative, loop.line, "AA001"):
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
        for line in facts.context_growth_inconclusive:
            report.analysis_warnings.append(
                AnalysisWarning(
                    code="AA013_INCONCLUSIVE_CONTEXT_GROWTH",
                    message="Context mutation and model use were recognized, but collection identity could not be proven.",
                    file=relative,
                    line=line,
                )
            )
        report.findings.extend(evaluate_file(relative, lines, facts))
    report.findings.extend(evaluate_project(project_facts))
    if config.rulepacks:
        plugin_result = evaluate_plugins(
            load_rule_plugins(config.rulepacks, root=scan_root),
            RuleContext(files=normalized_files),
        )
        report.findings.extend(plugin_result.findings)
        report.analysis_warnings.extend(plugin_result.warnings)
    filtered_findings = []
    for finding in report.findings:
        if is_suppressed(finding.file, finding.line, finding.rule_id):
            continue
        finding.excerpt, counts = redact_text(finding.excerpt)
        report.redactions.add(counts)
        filtered_findings.append(finding)
    report.findings = filtered_findings
    report.coverage.frameworks_detected = sorted(frameworks)
    if project_facts and any(facts.agent_present or facts.model_calls for _, _, facts in project_facts):
        applicable = [definition for definition in definitions if "static" in definition.tier]
        report.coverage.rules_evaluated = [
            definition.id for definition in applicable if definition.maturity == "stable"
        ]
        report.coverage.experimental_rules_evaluated = [
            definition.id for definition in applicable if definition.maturity == "experimental"
        ]
        report.coverage.rules_not_applicable = []
    elif files:
        report.coverage.rules_not_applicable = [definition.id for definition in definitions]
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
        candidates = []
        for candidate in collect_judgment_candidates(judgment_sources):
            if is_suppressed(candidate.file, candidate.line, candidate.rule_id):
                continue
            candidates.append(candidate)
        if judgment_client is None:
            try:
                from openai import OpenAI

                judgment_client = OpenAI(
                    max_retries=config.judgment.max_retries,
                    timeout=config.judgment.timeout_seconds,
                    base_url=config.judgment.base_url,
                )
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
        run_judgment(report, candidates, client=judgment_client, config=config.judgment)
    overrides = {key.upper(): value for key, value in config.rules.items()}
    report.findings = [
        finding
        for finding in report.findings
        if overrides.get(finding.rule_id) is None or overrides[finding.rule_id].enabled
    ]
    for finding in report.findings:
        override = overrides.get(finding.rule_id)
        if override and override.severity is not None:
            finding.severity = override.severity
    report.rule_results = _rule_results(report, judgment_requested=judgment)
    registry_payload = json.dumps(
        [definition.model_dump(mode="json") for definition in definitions],
        sort_keys=True,
    )
    report.metadata = ScanMetadata(
        duration_ms=max(0, round((time.monotonic() - started) * 1000)),
        repository_revision=_repository_revision(scan_root),
        configuration_fingerprint=content_fingerprint(config.model_dump_json()),
        rulepack_fingerprint=content_fingerprint(registry_payload),
    )
    return report


class AuditService:
    """Single application service shared by CLI and MCP interfaces."""

    def scan(
        self,
        root: str | Path,
        *,
        judgment: bool = False,
        send_code: bool = False,
        judgment_client: Any | None = None,
        extra_excludes: list[str] | None = None,
        severity_overrides: dict[str, str] | None = None,
        cancelled: Callable[[], bool] | None = None,
    ) -> Report:
        return _scan_path_impl(
            root,
            judgment=judgment,
            send_code=send_code,
            judgment_client=judgment_client,
            extra_excludes=extra_excludes,
            severity_overrides=severity_overrides,
            cancelled=cancelled,
        )


def scan_path(
    root: str | Path,
    *,
    judgment: bool = False,
    send_code: bool = False,
    judgment_client: Any | None = None,
    extra_excludes: list[str] | None = None,
    severity_overrides: dict[str, str] | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> Report:
    return AuditService().scan(
        root,
        judgment=judgment,
        send_code=send_code,
        judgment_client=judgment_client,
        extra_excludes=extra_excludes,
        severity_overrides=severity_overrides,
        cancelled=cancelled,
    )
