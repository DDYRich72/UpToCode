"""Anthropic Messages API and Claude Agent SDK evidence extraction."""

from __future__ import annotations

import ast

from uptocode.adapters.common import (
    assigned_calls,
    function_has_validation,
    function_is_destructive,
    keyword,
    literal,
    qualified_name,
)
from uptocode.evidence import LoopEvidence, ModelCallEvidence, NormalizedEvidence, ToolEvidence
from uptocode.models import AnalysisWarning


def _stop_reason_comparison(node: ast.AST, value: str) -> bool:
    return isinstance(node, ast.Compare) and any(
        isinstance(item, ast.Constant) and item.value == value for item in [*node.comparators]
    ) and any(
        isinstance(item, ast.Attribute) and item.attr == "stop_reason" for item in ast.walk(node.left)
    )


def extract_anthropic_evidence(tree: ast.Module, source: str, *, file: str) -> NormalizedEvidence:
    result = NormalizedEvidence(language="python")
    if not any(token in source for token in ("anthropic", "Anthropic", "ClaudeSDKClient")):
        return result
    assignments = assigned_calls(tree)
    client_controls: dict[str, tuple[bool, bool, bool]] = {}
    hooks = "PreToolUse" in source or "PostToolUse" in source
    for name, call in assignments.items():
        call_name = qualified_name(call.func)
        if call_name.endswith(("Anthropic", "AsyncAnthropic", "ClaudeSDKClient")):
            timeout = keyword(call, "timeout") is not None
            retry = keyword(call, "max_retries") is not None
            client_controls[name] = (timeout, retry, retry)
            result.frameworks.add("anthropic")
            result.agent_present = True
            result.first_agent_line = min(result.first_agent_line, call.lineno)

    protocol_lines: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.While):
            continue
        protocol = _stop_reason_comparison(node.test, "tool_use")
        if not protocol and isinstance(node.test, ast.Constant) and node.test.value is True:
            protocol = any(
                isinstance(candidate, ast.If)
                and _stop_reason_comparison(candidate.test, "end_turn")
                and any(isinstance(item, (ast.Break, ast.Return)) for item in candidate.body)
                for candidate in ast.walk(node)
            )
        if protocol:
            protocol_lines.add(node.lineno)
            result.loops.append(
                LoopEvidence(
                    line=node.lineno,
                    end_line=node.end_lineno,
                    framework="anthropic",
                    bound_kind="protocol",
                    detail="Claude tool loop terminates on the structured stop_reason protocol.",
                    provenance="stop_reason",
                )
            )
        else:
            segment = ast.get_source_segment(source, node) or ""
            if "messages.create" in segment and any(
                token in segment for token in ("content", "text", "DONE", "complete")
            ):
                result.loops.append(
                    LoopEvidence(
                        line=node.lineno,
                        end_line=node.end_lineno,
                        framework="anthropic",
                        bound_kind="cap-only",
                        detail="Claude loop relies on a numeric/text completion cap without stop_reason termination.",
                        provenance="text-completion",
                    )
                )
            elif "stop_reason" in segment:
                result.warnings.append(
                    AnalysisWarning(
                        code="AA001_INCONCLUSIVE_ANTHROPIC_LOOP",
                        message="Anthropic stop_reason handling was found but its termination contract was not recognized.",
                        file=file,
                        line=node.lineno,
                    )
                )

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            call_name = qualified_name(node.func)
            if call_name.endswith("messages.create"):
                owner = call_name.split(".", 1)[0]
                timeout, retry, backoff = client_controls.get(owner, (False, False, False))
                timeout = timeout or keyword(node, "timeout") is not None
                result.frameworks.add("anthropic")
                result.agent_present = True
                result.first_agent_line = min(result.first_agent_line, node.lineno)
                result.model_calls.append(
                    ModelCallEvidence(
                        line=node.lineno,
                        end_line=node.end_lineno,
                        framework="anthropic",
                        has_output_limit=keyword(node, "max_tokens") is not None,
                        has_timeout=timeout,
                        has_retry=retry,
                        has_backoff=backoff,
                        provenance="messages.create",
                    )
                )
                tools = keyword(node, "tools")
                if isinstance(tools, (ast.List, ast.Tuple)):
                    for item in tools.elts:
                        if not isinstance(item, ast.Dict):
                            continue
                        keys = {literal(key) for key in item.keys}
                        tool_name = next(
                            (
                                literal(value)
                                for key, value in zip(item.keys, item.values, strict=False)
                                if literal(key) == "name"
                            ),
                            "anthropic_tool",
                        )
                        result.tools.append(
                            ToolEvidence(
                                line=item.lineno,
                                framework="anthropic",
                                name=str(tool_name),
                                approval=hooks,
                                argument_risk="input_schema" not in keys,
                                provenance="tools-dict",
                            )
                        )
            if call_name.endswith("tool"):
                result.frameworks.add("anthropic-agent-sdk")
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            decorators = [
                qualified_name(item.func if isinstance(item, ast.Call) else item)
                for item in node.decorator_list
            ]
            if any(name.endswith("tool") for name in decorators) and "anthropic" in source.lower():
                result.frameworks.add("anthropic-agent-sdk")
                result.agent_present = True
                result.tools.append(
                    ToolEvidence(
                        line=node.lineno,
                        end_line=node.end_lineno,
                        framework="anthropic-agent-sdk",
                        name=node.name,
                        destructive=function_is_destructive(node),
                        approval=hooks,
                        argument_risk=not function_has_validation(node),
                        provenance="@tool",
                    )
                )
    if "server_tool" in source and "pause_turn" not in source:
        result.warnings.append(
            AnalysisWarning(
                code="ANTHROPIC_PAUSE_TURN_UNHANDLED",
                message="Server-tool usage was recognized without explicit pause_turn handling.",
                file=file,
            )
        )
    return result
