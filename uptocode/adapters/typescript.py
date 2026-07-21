"""Tree-sitter TypeScript/TSX evidence extraction without regex heuristics."""

from __future__ import annotations

from collections.abc import Iterator

from tree_sitter import Language, Node, Parser
import tree_sitter_typescript

from uptocode.evidence import LoopEvidence, ModelCallEvidence, NormalizedEvidence, ToolEvidence
from uptocode.models import AnalysisWarning


def _parser(*, tsx: bool) -> Parser:
    capsule = (
        tree_sitter_typescript.language_tsx()
        if tsx
        else tree_sitter_typescript.language_typescript()
    )
    return Parser(Language(capsule))


def _walk(node: Node) -> Iterator[Node]:
    stack = [node]
    while stack:
        current = stack.pop()
        yield current
        stack.extend(reversed(current.children))


def _text(node: Node | None, source: bytes) -> str:
    if node is None:
        return ""
    return source[node.start_byte : node.end_byte].decode("utf-8")


def _line(node: Node) -> int:
    return node.start_point.row + 1


def _end_line(node: Node) -> int:
    return node.end_point.row + 1


def _call_name(node: Node, source: bytes) -> str:
    return _text(node.child_by_field_name("function"), source)


def _object_pairs(node: Node, source: bytes) -> dict[str, Node]:
    pairs: dict[str, Node] = {}
    for candidate in _walk(node):
        if candidate.type not in {"pair", "pair_pattern"}:
            continue
        key = candidate.child_by_field_name("key")
        value = candidate.child_by_field_name("value")
        if key is None or value is None:
            continue
        pairs[_text(key, source).strip("'\"")] = value
    return pairs


def _contains_exit(node: Node) -> bool:
    for candidate in _walk(node):
        if candidate is not node and candidate.type in {
            "function_declaration",
            "function_expression",
            "arrow_function",
        }:
            continue
        if candidate.type in {"break_statement", "return_statement", "throw_statement"}:
            return True
    return False


def _is_true_condition(node: Node | None, source: bytes) -> bool:
    return _text(node, source).replace("(", "").replace(")", "").strip() == "true"


def extract_typescript_evidence(source: str, *, file: str) -> NormalizedEvidence:
    encoded = source.encode("utf-8")
    tree = _parser(tsx=file.lower().endswith(".tsx")).parse(encoded)
    root = tree.root_node
    result = NormalizedEvidence(language="typescript")
    if root.has_error:
        error = next((node for node in _walk(root) if node.is_error or node.is_missing), root)
        result.warnings.append(
            AnalysisWarning(
                code="TYPESCRIPT_PARSE_RECOVERY",
                message="TypeScript contained syntax errors; supported evidence was recovered where possible.",
                file=file,
                line=_line(error),
            )
        )

    global_timeout = False
    global_retry = False
    tracing_lines: list[int] = []
    for node in _walk(root):
        if node.type == "import_statement":
            statement = _text(node, encoded)
            if any(token in statement for token in ("@openai/agents", "openai")):
                result.frameworks.add("openai-agents-js")
            if "langgraph" in statement.lower():
                result.frameworks.add("langgraph-js")
            if any(token in statement.lower() for token in ("opentelemetry", "langsmith", "tracing")):
                tracing_lines.append(_line(node))
        if node.type != "call_expression":
            continue
        name = _call_name(node, encoded)
        pairs = _object_pairs(node, encoded)
        if name.endswith("AbortSignal.timeout"):
            global_timeout = True
        if any(key in pairs for key in ("timeout", "timeoutMs", "signal")):
            global_timeout = True
        if any(key in pairs for key in ("maxRetries", "max_retries", "retry")):
            global_retry = True

    result.observability_lines = sorted(set(tracing_lines))
    for node in _walk(root):
        if node.type == "while_statement":
            condition = node.child_by_field_name("condition")
            body = node.child_by_field_name("body")
            if _is_true_condition(condition, encoded):
                result.frameworks.add("custom-typescript")
                result.agent_present = True
                bounded = body is not None and _contains_exit(body)
                result.loops.append(
                    LoopEvidence(
                        _line(node),
                        "custom-typescript",
                        "custom" if bounded else "disabled",
                        "while (true) contains an exit" if bounded else "while (true) has no exit",
                        _end_line(node),
                        "tree-sitter",
                    )
                )
        elif node.type == "for_statement":
            condition = node.child_by_field_name("condition")
            body = node.child_by_field_name("body")
            if condition is None:
                result.frameworks.add("custom-typescript")
                result.agent_present = True
                bounded = body is not None and _contains_exit(body)
                result.loops.append(
                    LoopEvidence(
                        _line(node),
                        "custom-typescript",
                        "custom" if bounded else "disabled",
                        "for (;;) contains an exit" if bounded else "for (;;) has no exit",
                        _end_line(node),
                        "tree-sitter",
                    )
                )
        if node.type != "call_expression":
            continue
        name = _call_name(node, encoded)
        pairs = _object_pairs(node, encoded)
        if name.rsplit(".", 1)[-1] == "run" and (
            "openai-agents-js" in result.frameworks or "maxTurns" in pairs
        ):
            result.frameworks.add("openai-agents-js")
            result.agent_present = True
            max_turns = pairs.get("maxTurns")
            if max_turns is None:
                kind, detail = "sdk-default", "OpenAI Agents JS uses its bounded maxTurns default."
            elif _text(max_turns, encoded).strip() in {"null", "undefined"}:
                kind, detail = "disabled", "OpenAI Agents JS maxTurns is disabled."
            elif max_turns.type in {"number", "number_literal"}:
                kind, detail = "explicit", f"OpenAI Agents JS maxTurns={_text(max_turns, encoded)}."
            else:
                kind, detail = "unknown", "OpenAI Agents JS maxTurns is dynamically configured."
            result.loops.append(
                LoopEvidence(_line(node), "openai-agents-js", kind, detail, _end_line(node), "run-options")
            )
            result.has_run_budget = kind in {"explicit", "sdk-default"}
            result.model_calls.append(
                ModelCallEvidence(
                    _line(node),
                    "openai-agents-js",
                    any(key in pairs for key in ("maxTokens", "max_output_tokens")),
                    global_timeout,
                    global_retry,
                    global_retry,
                    _end_line(node),
                    "run",
                )
            )
        if name.endswith(("invoke", "ainvoke")) and (
            "langgraph-js" in result.frameworks or "recursionLimit" in pairs
        ):
            result.frameworks.add("langgraph-js")
            result.agent_present = True
            limit = pairs.get("recursionLimit")
            if limit is None:
                kind, detail = "sdk-default", "LangGraph.js uses its bounded recursion default."
            elif limit.type in {"number", "number_literal"}:
                kind, detail = "explicit", f"LangGraph.js recursionLimit={_text(limit, encoded)}."
            else:
                kind, detail = "unknown", "LangGraph.js recursionLimit is dynamically configured."
            result.loops.append(
                LoopEvidence(_line(node), "langgraph-js", kind, detail, _end_line(node), "invoke-config")
            )
            result.has_run_budget = kind in {"explicit", "sdk-default"}
        if name.rsplit(".", 1)[-1] == "tool":
            result.agent_present = True
            parameters = pairs.get("parameters")
            validated = parameters is not None and "z.object" in _text(parameters, encoded)
            tool_name = _text(pairs.get("name"), encoded).strip("'\"") or "typescript_tool"
            result.tools.append(
                ToolEvidence(
                    _line(node),
                    "typescript",
                    tool_name,
                    argument_risk=not validated,
                    end_line=_end_line(node),
                    provenance="tool-parameters",
                    confidence="medium",
                )
            )

    if result.agent_present:
        first_lines = (
            [item.line for item in result.loops]
            + [item.line for item in result.model_calls]
            + [item.line for item in result.tools]
        )
        result.first_agent_line = min(first_lines, default=1)
    if any(
        item.bound_kind == "unknown" for item in result.loops
    ):
        result.warnings.append(
            AnalysisWarning(
                code="TYPESCRIPT_DYNAMIC_CONFIGURATION",
                message="A TypeScript framework bound is dynamic and could not be resolved statically.",
                file=file,
            )
        )
    return result
