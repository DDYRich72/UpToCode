"""CrewAI framework evidence extraction."""

from __future__ import annotations

import ast

from uptocode.adapters.common import (
    function_has_validation,
    function_is_destructive,
    keyword,
    literal,
    qualified_name,
)
from uptocode.evidence import LoopEvidence, ModelCallEvidence, NormalizedEvidence, ToolEvidence
from uptocode.models import AnalysisWarning


def extract_crewai_evidence(tree: ast.Module, source: str, *, file: str) -> NormalizedEvidence:
    result = NormalizedEvidence(language="python")
    if "crewai" not in source.lower():
        return result
    result.frameworks.add("crewai")
    agents: dict[str, ast.Call] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and isinstance(node.value, ast.Call):
            if qualified_name(node.value.func).endswith("Agent"):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    if isinstance(target, ast.Name):
                        agents[target.id] = node.value
        if isinstance(node, ast.Call) and qualified_name(node.func).endswith("Agent"):
            result.agent_present = True
            result.first_agent_line = min(result.first_agent_line, node.lineno)
            max_iter = keyword(node, "max_iter")
            max_time = keyword(node, "max_execution_time")
            if max_iter is None:
                kind, detail = "sdk-default", "CrewAI Agent uses its documented bounded max_iter default."
            elif literal(max_iter) is None and isinstance(max_iter, ast.Constant):
                kind, detail = "disabled", "CrewAI max_iter=None disables the iteration ceiling."
            elif isinstance(literal(max_iter), int):
                kind, detail = "explicit", f"CrewAI max_iter={literal(max_iter)}."
            else:
                kind, detail = "unknown", "CrewAI max_iter is dynamically configured."
            result.loops.append(LoopEvidence(node.lineno, "crewai", kind, detail, node.end_lineno, "Agent"))
            result.has_run_budget = result.has_run_budget or max_iter is not None or max_time is not None
        if isinstance(node, ast.Call) and qualified_name(node.func).endswith("kickoff"):
            result.agent_present = True
            timeout = any(keyword(call, "max_execution_time") is not None for call in agents.values())
            retry = "max_retry_limit" in source or "max_retries" in source or "retry" in source
            result.model_calls.append(
                ModelCallEvidence(
                    node.lineno,
                    "crewai",
                    has_output_limit=any(keyword(call, "max_iter") is not None for call in agents.values()),
                    has_timeout=timeout,
                    has_retry=retry,
                    has_backoff=retry,
                    end_line=node.end_lineno,
                    provenance="kickoff",
                )
            )
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            decorators = [qualified_name(item.func if isinstance(item, ast.Call) else item) for item in node.decorator_list]
            if any(name.endswith("tool") for name in decorators):
                result.tools.append(
                    ToolEvidence(
                        node.lineno,
                        "crewai",
                        node.name,
                        function_is_destructive(node),
                        any("approval" in name.lower() for name in decorators),
                        not function_has_validation(node),
                        node.end_lineno,
                        "@tool",
                    )
                )
    if "Process." in source and not any(value in source for value in ("Process.sequential", "Process.hierarchical")):
        result.warnings.append(
            AnalysisWarning(
                code="UNSUPPORTED_CREWAI_PROCESS",
                message="CrewAI process configuration was not recognized as sequential or hierarchical.",
                file=file,
            )
        )
    return result
