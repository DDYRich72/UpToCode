"""Conservative project facts for the Python static rulepack."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field


MODEL_METHODS = {"create", "parse", "run", "run_sync", "run_streamed"}
SIDE_EFFECT_NAMES = {
    "delete",
    "remove",
    "unlink",
    "write",
    "write_text",
    "send",
    "pay",
    "execute",
    "run",
    "save",
    "save_result",
}
DESTRUCTIVE_PREFIXES = ("delete", "remove", "send", "pay", "write", "update", "create")


def qualified_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = qualified_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


@dataclass(frozen=True)
class ModelCallFact:
    line: int
    has_output_limit: bool
    has_timeout: bool
    has_retry: bool


@dataclass(frozen=True)
class ToolFact:
    line: int
    name: str
    destructive: bool
    approval: bool
    argument_risk: bool


@dataclass(frozen=True)
class SinkFact:
    line: int
    kind: str


@dataclass
class FileFacts:
    agent_present: bool = False
    first_agent_line: int = 1
    model_calls: list[ModelCallFact] = field(default_factory=list)
    tools: list[ToolFact] = field(default_factory=list)
    risky_sinks: list[SinkFact] = field(default_factory=list)
    raw_output_sinks: list[SinkFact] = field(default_factory=list)
    hardcoded_secrets: list[int] = field(default_factory=list)
    secret_prompt_exposures: list[int] = field(default_factory=list)
    has_run_budget: bool = False
    has_observability: bool = False
    has_eval_marker: bool = False


def _decorator_approval(decorator: ast.AST) -> bool:
    if not isinstance(decorator, ast.Call):
        return False
    return any(
        keyword.arg in {"needs_approval", "require_approval"}
        and not (isinstance(keyword.value, ast.Constant) and keyword.value.value is False)
        for keyword in decorator.keywords
    )


def _is_tool(function: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return any("function_tool" in qualified_name(decorator.func if isinstance(decorator, ast.Call) else decorator) for decorator in function.decorator_list)


def _function_has_validation(function: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return any(isinstance(node, (ast.If, ast.Assert, ast.Raise)) for node in ast.walk(function))


def _call_uses_parameter(call: ast.Call, parameters: set[str]) -> bool:
    return any(isinstance(node, ast.Name) and node.id in parameters for arg in call.args for node in ast.walk(arg))


def _contains_raw_model_output(node: ast.AST) -> bool:
    return any(
        isinstance(candidate, ast.Attribute)
        and candidate.attr in {"output_text", "content", "final_output"}
        for candidate in ast.walk(node)
    )


def _contains_validation(node: ast.AST) -> bool:
    return any(
        isinstance(candidate, ast.Call)
        and qualified_name(candidate.func).endswith(("model_validate", "parse_obj", "validate_python"))
        for candidate in ast.walk(node)
    )


def _is_side_effect_call(call_name: str) -> bool:
    if "Runner.run" in call_name or "responses." in call_name:
        return False
    terminal = call_name.rsplit(".", 1)[-1].lower()
    return terminal in SIDE_EFFECT_NAMES or terminal.startswith(DESTRUCTIVE_PREFIXES + ("save",))


def analyze_source(tree: ast.Module, source: str) -> FileFacts:
    facts = FileFacts()
    facts.has_run_budget = "BUDGET" in source and any(
        isinstance(node, (ast.Compare, ast.If)) for node in ast.walk(tree)
    )
    facts.has_observability = any(
        token in source
        for token in ("logging.", "logger.", "trace(", "tracing", "start_span")
    )
    facts.has_eval_marker = "archagent-audit: eval agent" in source
    client_timeout = False
    client_retry = False
    environment_secrets: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        value = node.value
        is_environment = isinstance(value, ast.Subscript) and qualified_name(value.value).endswith("os.environ")
        is_getenv = isinstance(value, ast.Call) and qualified_name(value.func).endswith(("os.getenv", "getenv"))
        if not (is_environment or is_getenv):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        environment_secrets.update(target.id for target in targets if isinstance(target, ast.Name))

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            call_name = qualified_name(node.func)
            if call_name.endswith("OpenAI"):
                client_timeout |= any(keyword.arg == "timeout" for keyword in node.keywords)
                client_retry |= any(keyword.arg in {"max_retries", "retry"} for keyword in node.keywords)
            is_agent = call_name.endswith("Agent") or "Runner.run" in call_name
            is_model = "responses." in call_name and call_name.rsplit(".", 1)[-1] in MODEL_METHODS
            if is_agent or is_model:
                facts.agent_present = True
                facts.first_agent_line = min(facts.first_agent_line, node.lineno) if facts.first_agent_line != 1 else node.lineno
            if is_model:
                for keyword in node.keywords:
                    if keyword.arg not in {"input", "prompt", "messages"}:
                        continue
                    if any(isinstance(candidate, ast.Name) and candidate.id in environment_secrets for candidate in ast.walk(keyword.value)):
                        facts.secret_prompt_exposures.append(node.lineno)
                facts.model_calls.append(
                    ModelCallFact(
                        line=node.lineno,
                        has_output_limit=any(keyword.arg in {"max_output_tokens", "max_tokens"} for keyword in node.keywords),
                        has_timeout=client_timeout or any(keyword.arg == "timeout" for keyword in node.keywords),
                        has_retry=client_retry or any(keyword.arg in {"retry", "max_retries"} for keyword in node.keywords),
                    )
                )
            terminal = call_name.rsplit(".", 1)[-1]
            if _is_side_effect_call(call_name) and _contains_raw_model_output(node) and not _contains_validation(node):
                facts.raw_output_sinks.append(SinkFact(node.lineno, terminal))
            parameterized_sql = terminal == "execute" and len(node.args) >= 2
            if _is_side_effect_call(call_name) and not parameterized_sql and any(
                isinstance(candidate, ast.Name)
                and ("arg" in candidate.id.lower() or "model" in candidate.id.lower())
                for argument in node.args
                for candidate in ast.walk(argument)
            ):
                facts.risky_sinks.append(SinkFact(node.lineno, terminal))
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value.startswith("sk-") and len(node.value) >= 20:
                facts.hardcoded_secrets.append(node.lineno)

    for function in [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]:
        is_tool = _is_tool(function)
        if is_tool:
            facts.agent_present = True
        parameters = {argument.arg for argument in function.args.args}
        validation = _function_has_validation(function)
        destructive = function.name.lower().startswith(DESTRUCTIVE_PREFIXES)
        argument_risk = False
        for candidate in ast.walk(function):
            if not isinstance(candidate, ast.Call):
                continue
            call_name = qualified_name(candidate.func)
            terminal = call_name.rsplit(".", 1)[-1]
            if _is_side_effect_call(call_name):
                parameterized_sql = terminal == "execute" and len(candidate.args) >= 2
                if _call_uses_parameter(candidate, parameters) and not validation and not parameterized_sql:
                    argument_risk = True
                    facts.risky_sinks.append(SinkFact(candidate.lineno, terminal))
        if is_tool:
            facts.tools.append(
                ToolFact(
                    line=function.lineno,
                    name=function.name,
                    destructive=destructive,
                    approval=any(_decorator_approval(item) for item in function.decorator_list),
                    argument_risk=argument_risk,
                )
            )
    return facts
