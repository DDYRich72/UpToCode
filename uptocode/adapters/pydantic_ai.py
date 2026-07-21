"""PydanticAI framework evidence extraction."""

from __future__ import annotations

import ast

from uptocode.adapters.common import assigned_calls, function_has_validation, function_is_destructive, keyword, qualified_name
from uptocode.evidence import ModelCallEvidence, NormalizedEvidence, ToolEvidence
from uptocode.models import AnalysisWarning


def extract_pydantic_ai_evidence(tree: ast.Module, source: str, *, file: str) -> NormalizedEvidence:
    result = NormalizedEvidence(language="python")
    if "pydantic_ai" not in source:
        return result
    result.frameworks.add("pydantic-ai")
    assignments = assigned_calls(tree)
    limits = {
        name: call
        for name, call in assignments.items()
        if qualified_name(call.func).endswith("UsageLimits")
    }
    settings = {
        name: call
        for name, call in assignments.items()
        if qualified_name(call.func).endswith("ModelSettings")
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and qualified_name(node.func).endswith("Agent"):
            result.agent_present = True
            result.first_agent_line = min(result.first_agent_line, node.lineno)
        if isinstance(node, ast.Call) and qualified_name(node.func).endswith((".run", ".run_sync", ".run_stream")):
            usage = keyword(node, "usage_limits")
            usage_call = usage if isinstance(usage, ast.Call) else limits.get(usage.id) if isinstance(usage, ast.Name) else None
            setting = keyword(node, "model_settings")
            setting_call = setting if isinstance(setting, ast.Call) else settings.get(setting.id) if isinstance(setting, ast.Name) else None
            request_limit = keyword(usage_call, "request_limit") if isinstance(usage_call, ast.Call) else None
            token_limit = keyword(usage_call, "total_tokens_limit") if isinstance(usage_call, ast.Call) else None
            timeout = keyword(setting_call, "timeout") if isinstance(setting_call, ast.Call) else None
            retry = keyword(setting_call, "max_retries") if isinstance(setting_call, ast.Call) else None
            if usage is not None and usage_call is None:
                result.warnings.append(
                    AnalysisWarning(
                        code="AA002_INCONCLUSIVE_PYDANTIC_USAGE_LIMITS",
                        message="PydanticAI usage limits are dynamically configured.",
                        file=file,
                        line=node.lineno,
                    )
                )
            result.model_calls.append(
                ModelCallEvidence(
                    node.lineno,
                    "pydantic-ai",
                    token_limit is not None,
                    timeout is not None,
                    retry is not None,
                    retry is not None,
                    node.end_lineno,
                    "Agent.run",
                )
            )
            result.has_run_budget = result.has_run_budget or request_limit is not None or token_limit is not None
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            decorators = [qualified_name(item.func if isinstance(item, ast.Call) else item) for item in node.decorator_list]
            if any(name.endswith(".tool") or name.endswith(".tool_plain") for name in decorators):
                result.agent_present = True
                result.tools.append(
                    ToolEvidence(
                        node.lineno,
                        "pydantic-ai",
                        node.name,
                        function_is_destructive(node),
                        any("approval" in name.lower() for name in decorators),
                        not function_has_validation(node),
                        node.end_lineno,
                        "@agent.tool",
                    )
                )
    return result
