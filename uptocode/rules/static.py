"""Evidence-backed Python static rules beyond AA001."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from uptocode.analysis import FileFacts
from uptocode.fingerprints import finding_fingerprint
from uptocode.models import (
    Evidence,
    Finding,
    FindingContext,
    Remediation,
    Verdict,
)
from uptocode.rules.registry import core_rule_map


def _finding(
    rule_id: str,
    title: str,
    file: str,
    line: int,
    kind: str,
    detail: str,
    excerpt: str,
    recommended: str,
    complexity: Literal["trivial", "moderate", "complex"] = "moderate",
) -> Finding:
    definition = core_rule_map()[rule_id]
    return Finding(
        rule_id=rule_id,
        severity=definition.severity,
        tier="static",
        maturity=definition.maturity,
        title=title,
        file=file,
        line=line,
        fingerprint=finding_fingerprint(
            rule_id, file, kind, detail=detail, excerpt=excerpt
        ),
        evidence=[Evidence(kind=kind, detail=detail)],
        verdict=Verdict(
            observed=detail,
            implies=f"The architecture exhibits {title.lower()}.",
            recommended=recommended,
            tradeoff="The control adds implementation and maintenance overhead.",
        ),
        citations=[citation.to_public() for citation in definition.citations],
        excerpt=excerpt,
        context=FindingContext(),
        remediation=Remediation(complexity=complexity),
    )


def evaluate_file(file: str, lines: list[str], facts: FileFacts) -> list[Finding]:
    findings: list[Finding] = []

    def excerpt(line: int) -> str:
        return "\n".join(lines[max(0, line - 2) : min(len(lines), line + 1)])
    for call in facts.model_calls:
        missing: list[str] = []
        if not call.has_output_limit:
            missing.append("output-token ceiling")
        if not facts.has_run_budget:
            missing.append("whole-run budget")
        if missing:
            findings.append(_finding("AA002", "Missing run budget control", file, call.line, "missing-budget-controls", f"Missing {', '.join(missing)}.", excerpt(call.line), "Enforce both an output cap and a whole-run budget."))
        if not call.has_timeout:
            findings.append(_finding("AA007", "Missing model-call timeout", file, call.line, "missing-timeout", "Model call has no recognized timeout.", excerpt(call.line), "Set a bounded request timeout."))
        if not call.has_retry:
            findings.append(_finding("AA007", "Missing safe retry policy", file, call.line, "missing-retry", "Model call has no recognized bounded retry policy.", excerpt(call.line), "Add bounded backoff only when replay is safe."))
        elif not call.has_backoff:
            findings.append(_finding("AA007", "Retry policy lacks backoff", file, call.line, "retry-without-backoff", "Retry policy has no recognized exponential or randomized backoff.", excerpt(call.line), "Add bounded exponential or randomized backoff when replay is safe."))
    for growth in facts.context_growth:
        findings.append(
            _finding(
                "AA013",
                "Unbounded context growth",
                file,
                growth.line,
                "context-list-grows-in-loop",
                growth.detail,
                excerpt(growth.line),
                "Bound retained context with semantic summarization or explicit truncation before the next model call.",
            )
        )
    for transport in facts.mcp_transports:
        if not transport.authenticated:
            findings.append(
                _finding(
                    "AA014",
                    "Network MCP transport without authentication evidence",
                    file,
                    transport.line,
                    "mcp-network-without-auth",
                    transport.detail + " No recognized authentication boundary is composed.",
                    excerpt(transport.line),
                    "Add transport-level bearer/OAuth verification before exposing the MCP application.",
                    "complex",
                )
            )
    for mcp_tool in facts.mcp_tools:
        if not mcp_tool.has_annotations:
            findings.append(
                _finding(
                    "AA015",
                    "MCP tool has no annotations",
                    file,
                    mcp_tool.line,
                    "mcp-tool-without-annotations",
                    f"Registered MCP tool {mcp_tool.name} has no recognized ToolAnnotations.",
                    excerpt(mcp_tool.line),
                    "Declare read-only, destructive, idempotent, and open-world hints explicitly.",
                )
            )
        if not mcp_tool.strict_arguments:
            findings.append(
                _finding(
                    "AA016",
                    "MCP tool arguments accept unknown fields",
                    file,
                    mcp_tool.line,
                    "mcp-tool-arguments-not-strict",
                    f"Registered MCP tool {mcp_tool.name} has no recognized strict argument model or schema hardening.",
                    excerpt(mcp_tool.line),
                    "Reject unknown argument fields with a strict model or explicit additionalProperties=false hardening.",
                )
            )
        if mcp_tool.generic_error:
            findings.append(
                _finding(
                    "AA017",
                    "Undifferentiated tool error",
                    file,
                    mcp_tool.line,
                    "generic-tool-error",
                    f"Registered MCP tool {mcp_tool.name} returns one generic error without category or retryability evidence.",
                    excerpt(mcp_tool.line),
                    "Return structured tool errors that distinguish validation, permission, transient, and business failures and identify retryability.",
                )
            )
    for policy in facts.policy_prompts:
        findings.append(
            _finding(
                "AA018",
                "Prompt-only policy enforcement",
                file,
                policy.line,
                "critical-policy-only-in-prompt",
                policy.detail,
                excerpt(policy.line),
                "Enforce the prerequisite in a tool hook, interceptor, constrained tool selection, or the tool body before the side effect.",
                "complex",
            )
        )
    for standard_tool in facts.tools:
        if standard_tool.destructive and not standard_tool.approval:
            findings.append(_finding("AA003", "Ungated destructive action", file, standard_tool.line, "missing-approval", f"Tool {standard_tool.name} can change state without a recognized approval gate.", excerpt(standard_tool.line), "Require an explicit approval mechanism before execution."))
        if standard_tool.argument_risk:
            findings.append(_finding("AA004", "Unvalidated tool arguments", file, standard_tool.line, "model-arg-to-sensitive-sink", f"Tool {standard_tool.name} sends an argument to a sensitive sink without recognized validation.", excerpt(standard_tool.line), "Validate and constrain arguments before the sink."))
    for sink in facts.risky_sinks:
        if not any(tool.argument_risk and tool.line <= sink.line for tool in facts.tools):
            findings.append(_finding("AA004", "Unvalidated tool arguments", file, sink.line, "model-arg-to-sensitive-sink", f"A model-controlled value reaches {sink.kind} without recognized validation.", excerpt(sink.line), "Validate and constrain arguments before the sink."))
    for line in facts.hardcoded_secrets:
        findings.append(_finding("AA006", "Secret exposure", file, line, "hardcoded-secret", "A hardcoded API credential is present in source.", excerpt(line), "Load the secret from a protected runtime environment and keep it out of prompts and logs."))
    for line in facts.hardcoded_pii:
        findings.append(_finding("AA006", "PII exposure", file, line, "hardcoded-pii", "A hardcoded email address or US Social Security number is present in agent source.", excerpt(line), "Remove personal data from source and pass only the minimum protected value at runtime."))
    for line in facts.secret_prompt_exposures:
        findings.append(_finding("AA006", "Secret exposure", file, line, "secret-in-prompt", "A secret-derived environment value is interpolated into a model prompt.", excerpt(line), "Keep credentials out of model inputs and pass them only to the trusted integration that needs them."))
    for sink in facts.raw_output_sinks:
        findings.append(_finding("AA010", "Unvalidated model output before side effect", file, sink.line, "raw-output-to-side-effect", f"Raw model output reaches {sink.kind} without schema validation.", excerpt(sink.line), "Validate model output against a strict schema and domain rules first."))
    return findings


def evaluate_project(
    files: Iterable[tuple[str, list[str], FileFacts]],
) -> list[Finding]:
    entries = list(files)
    agent_entries = [entry for entry in entries if entry[2].agent_present]
    if not agent_entries:
        return []
    findings: list[Finding] = []
    has_eval = any(
        facts.has_eval_marker
        or (
            file.rsplit("/", 1)[-1].startswith("test_")
            and any(
                token in "\n".join(lines)
                for token in ("Runner.run", "run_agent(", "agent.run(", "Agent(")
            )
        )
        for file, lines, facts in entries
    )
    if not has_eval:
        file, lines, facts = agent_entries[0]
        line = facts.first_agent_line
        findings.append(_finding("AA011", "No agent eval coverage", file, line, "missing-eval", "Supported agent code has no recognized test or eval artifact.", "\n".join(lines[max(0, line - 2):line + 1]), "Add representative evals that exercise the agent entrypoint."))
    for file, lines, facts in agent_entries:
        if (
            any(abs(line - facts.first_agent_line) <= 25 for line in facts.observability_lines)
            or ((facts.mcp_transports or facts.mcp_tools) and facts.has_observability)
        ):
            continue
        line = facts.first_agent_line
        findings.append(_finding("AA012", "No agent observability", file, line, "missing-observability", "Agent code has no recognized logging or tracing evidence.", "\n".join(lines[max(0, line - 2):line + 1]), "Log or trace loop decisions and tool execution without sensitive payloads."))
    return findings
