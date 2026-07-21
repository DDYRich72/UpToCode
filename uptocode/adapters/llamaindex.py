"""LlamaIndex agent evidence extraction."""

from __future__ import annotations

import ast

from uptocode.adapters.common import keyword, literal, qualified_name
from uptocode.evidence import LoopEvidence, ModelCallEvidence, NormalizedEvidence, ToolEvidence
from uptocode.models import AnalysisWarning


AGENT_NAMES = ("FunctionAgent", "ReActAgent", "AgentWorkflow")


def extract_llamaindex_evidence(tree: ast.Module, source: str, *, file: str) -> NormalizedEvidence:
    result = NormalizedEvidence(language="python")
    if "llama_index" not in source:
        return result
    result.frameworks.add("llamaindex")
    has_timeout = "timeout=" in source
    has_retry = "max_retries=" in source
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and qualified_name(node.func).endswith(AGENT_NAMES):
            result.agent_present = True
            result.first_agent_line = min(result.first_agent_line, node.lineno)
            iterations = keyword(node, "max_iterations")
            if iterations is None:
                result.warnings.append(
                    AnalysisWarning(
                        code="AA001_INCONCLUSIVE_LLAMAINDEX_BOUND",
                        message="LlamaIndex agent construction has no statically visible iteration bound.",
                        file=file,
                        line=node.lineno,
                    )
                )
            else:
                value = literal(iterations)
                kind = "explicit" if isinstance(value, int) else "unknown"
                result.loops.append(
                    LoopEvidence(
                        node.lineno,
                        "llamaindex",
                        kind,
                        f"LlamaIndex max_iterations={value!r}.",
                        node.end_lineno,
                        "agent-constructor",
                    )
                )
                result.has_run_budget = isinstance(value, int)
            tools = keyword(node, "tools")
            if isinstance(tools, (ast.List, ast.Tuple)):
                for item in tools.elts:
                    result.tools.append(
                        ToolEvidence(item.lineno, "llamaindex", qualified_name(item) or "tool", provenance="tools-list")
                    )
            if keyword(node, "output_cls") is not None:
                result.has_run_budget = result.has_run_budget or False
        if isinstance(node, ast.Call) and qualified_name(node.func).endswith((".run", ".chat")):
            result.model_calls.append(
                ModelCallEvidence(
                    node.lineno,
                    "llamaindex",
                    has_output_limit="max_tokens" in source or "token_limit" in source,
                    has_timeout=has_timeout,
                    has_retry=has_retry,
                    has_backoff=has_retry,
                    end_line=node.end_lineno,
                    provenance="agent-run",
                )
            )
        if isinstance(node, ast.Call) and qualified_name(node.func).endswith("Memory.from_defaults"):
            result.has_run_budget = result.has_run_budget or keyword(node, "token_limit") is not None
    custom_workflow = any(
        isinstance(node, ast.ClassDef)
        and any(qualified_name(base).endswith("AgentWorkflow") for base in node.bases)
        for node in ast.walk(tree)
    )
    if custom_workflow and not result.agent_present:
        result.warnings.append(
            AnalysisWarning(
                code="UNSUPPORTED_LLAMAINDEX_WORKFLOW",
                message="A custom LlamaIndex workflow subclass is outside static coverage.",
                file=file,
            )
        )
    return result
