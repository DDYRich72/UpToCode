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
from uptocode.analysis import (
    FileFacts,
    ModelCallFact,
    ToolFact,
    analyze_source,
    qualified_name,
)
from uptocode.adapters.registry import extract_framework_evidence
from uptocode.adapters.python import PythonEvidence, extract_python_evidence
from uptocode.adapters.typescript import extract_typescript_evidence
from uptocode.config import (
    SUPPORTED_SOURCE_EXTENSIONS,
    RuleOverride,
    discover_source_files_detailed,
    load_config,
)
from uptocode.fingerprints import content_fingerprint
from uptocode.judgment import run_judgment
from uptocode.judgment_candidates import collect_judgment_candidates
from uptocode.models import (
    AnalysisWarning,
    Coverage,
    LanguageCoverage,
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


TYPESCRIPT_STATIC_RULES = {"AA001", "AA002", "AA004", "AA007", "AA012"}


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
    if not target.exists() or (
        target.is_file() and target.suffix.lower() not in SUPPORTED_SOURCE_EXTENSIONS
    ):
        raise ValueError(f"Scan target must be a supported source file or directory: {target}")
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
        files, skipped_details = discover_source_files_detailed(scan_root, config)
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
    typescript_project_facts: list[tuple[str, list[str], FileFacts]] = []
    judgment_sources: list[tuple[str, str]] = []
    normalized_files: list[NormalizedFileEvidence] = []
    total_source_size = 0
    discovered_by_language = {
        "python": sum(path.suffix.lower() == ".py" for path in files),
        "typescript": sum(path.suffix.lower() in {".ts", ".tsx", ".mts"} for path in files),
    }
    analyzed_by_language = {"python": 0, "typescript": 0}
    agent_by_language = {"python": False, "typescript": False}
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
            is_python = path.suffix.lower() == ".py"
            tree: ast.Module | None
            if is_python:
                evidence = extract_python_evidence(source)
                tree = ast.parse(source)
                facts = analyze_source(tree, source)
                framework_evidence = extract_framework_evidence(tree, source, file=relative)
                language = "python"
            else:
                evidence = PythonEvidence()
                tree = None
                facts = FileFacts()
                framework_evidence = extract_typescript_evidence(source, file=relative)
                language = "typescript"
        except OSError:
            report.analysis_warnings.append(
                AnalysisWarning(
                    code="FILE_READ_ERROR",
                    message="Source could not be read; remaining files were preserved.",
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
        has_structural_tool_wiring = tree is not None and any(
            (
                isinstance(node, ast.Call)
                and any(keyword.arg == "tools" for keyword in node.keywords)
            )
            or (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and any(
                    qualified_name(decorator.func if isinstance(decorator, ast.Call) else decorator).endswith("tool")
                    for decorator in node.decorator_list
                )
            )
            for node in ast.walk(tree)
        )
        if tree is not None and (
            has_structural_tool_wiring
            and "@function_tool" not in source
            and any(token in source for token in ("Agent", "graph", "langgraph"))
            and not framework_evidence.frameworks
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
        analyzed_by_language[language] += 1
        if tree is not None:
            judgment_sources.append((relative, source))
        has_agent_reference = tree is not None and any(
            isinstance(node, (ast.Name, ast.Attribute))
            and any(
                token in qualified_name(node)
                for token in ("Agent", "Runner", "responses", "function_tool", "graph")
            )
            for node in ast.walk(tree)
        )
        has_dynamic_dispatch = tree is not None and any(
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
        protocol_lines = {
            loop.line
            for loop in framework_evidence.loops
            if loop.bound_kind == "protocol"
        }
        if protocol_lines:
            evidence.loops = [
                loop
                for loop in evidence.loops
                if not (loop.line in protocol_lines and loop.framework == "custom-python")
            ]
        evidence.loops.extend(framework_evidence.loops)
        evidence.frameworks.update(framework_evidence.frameworks)
        evidence.warnings.extend(framework_evidence.warnings)
        facts.agent_present = facts.agent_present or framework_evidence.agent_present
        if framework_evidence.agent_present:
            facts.first_agent_line = min(
                facts.first_agent_line, framework_evidence.first_agent_line
            )
        facts.has_run_budget = facts.has_run_budget or framework_evidence.has_run_budget
        facts.observability_lines.extend(framework_evidence.observability_lines)
        facts.has_observability = bool(facts.observability_lines)
        facts.model_calls.extend(
            ModelCallFact(
                line=item.line,
                has_output_limit=item.has_output_limit,
                has_timeout=item.has_timeout,
                has_retry=item.has_retry,
                has_backoff=item.has_backoff,
            )
            for item in framework_evidence.model_calls
        )
        facts.tools.extend(
            ToolFact(
                line=item.line,
                name=item.name,
                destructive=item.destructive,
                approval=item.approval,
                argument_risk=item.argument_risk,
            )
            for item in framework_evidence.tools
        )
        report.analysis_warnings.extend(evidence.warnings)
        frameworks.update(evidence.frameworks)
        agent_by_language[language] = agent_by_language[language] or facts.agent_present
        lines = source.splitlines()
        suppression_index, suppression_warnings = parse_suppressions(lines, file=relative)
        suppression_indexes[relative] = suppression_index
        report.suppression_details.extend(item.detail for item in suppression_index.directives)
        report.analysis_warnings.extend(suppression_warnings)
        if language == "python":
            project_facts.append((relative, lines, facts))
        else:
            typescript_project_facts.append((relative, lines, facts))
        normalized_files.append(
            NormalizedFileEvidence(
                file=relative,
                language=language,
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
    report.findings.extend(
        finding
        for finding in evaluate_project(typescript_project_facts)
        if finding.rule_id == "AA012"
    )
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
    language_coverage: list[LanguageCoverage] = []
    for language in ("python", "typescript"):
        if not discovered_by_language[language]:
            continue
        if language == "python" and agent_by_language[language]:
            applicable_ids = {definition.id for definition in definitions}
            evaluated = [definition for definition in definitions if "static" in definition.tier]
        elif language == "typescript" and agent_by_language[language]:
            applicable_ids = TYPESCRIPT_STATIC_RULES
            evaluated = [
                definition
                for definition in definitions
                if definition.id in TYPESCRIPT_STATIC_RULES and "static" in definition.tier
            ]
        else:
            applicable_ids = set()
            evaluated = []
        language_coverage.append(
            LanguageCoverage(
                language=language,  # type: ignore[arg-type]
                files_discovered=discovered_by_language[language],
                files_analyzed=analyzed_by_language[language],
                rules_evaluated=[
                    definition.id for definition in evaluated if definition.maturity == "stable"
                ],
                experimental_rules_evaluated=[
                    definition.id
                    for definition in evaluated
                    if definition.maturity == "experimental"
                ],
                rules_not_applicable=[
                    definition.id for definition in definitions if definition.id not in applicable_ids
                ],
            )
        )
    report.coverage.language_coverage = language_coverage
    if language_coverage and any(agent_by_language.values()):
        evaluated_ids = {
            rule_id
            for item in language_coverage
            for rule_id in item.rules_evaluated
        }
        experimental_ids = {
            rule_id
            for item in language_coverage
            for rule_id in item.experimental_rules_evaluated
        }
        not_applicable_sets = [set(item.rules_not_applicable) for item in language_coverage]
        globally_not_applicable = set.intersection(*not_applicable_sets) if not_applicable_sets else set()
        report.coverage.rules_evaluated = sorted(evaluated_ids)
        report.coverage.experimental_rules_evaluated = sorted(experimental_ids)
        report.coverage.rules_not_applicable = sorted(globally_not_applicable)
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
