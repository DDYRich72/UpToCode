"""Conservative project facts for the Python static rulepack."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field

from uptocode.redaction import contains_pii


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
    has_backoff: bool


@dataclass(frozen=True)
class ContextGrowthFact:
    line: int
    collection: str
    detail: str


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


@dataclass(frozen=True)
class McpTransportFact:
    line: int
    authenticated: bool
    detail: str


@dataclass(frozen=True)
class McpToolFact:
    line: int
    name: str
    has_annotations: bool
    strict_arguments: bool
    generic_error: bool


@dataclass(frozen=True)
class PolicyPromptFact:
    line: int
    detail: str


@dataclass(frozen=True)
class InconclusiveFact:
    line: int
    code: str
    detail: str


@dataclass
class FileFacts:
    agent_present: bool = False
    first_agent_line: int = 1
    model_calls: list[ModelCallFact] = field(default_factory=list)
    context_growth: list[ContextGrowthFact] = field(default_factory=list)
    context_growth_inconclusive: list[int] = field(default_factory=list)
    tools: list[ToolFact] = field(default_factory=list)
    risky_sinks: list[SinkFact] = field(default_factory=list)
    raw_output_sinks: list[SinkFact] = field(default_factory=list)
    hardcoded_secrets: list[int] = field(default_factory=list)
    hardcoded_pii: list[int] = field(default_factory=list)
    secret_prompt_exposures: list[int] = field(default_factory=list)
    has_run_budget: bool = False
    has_observability: bool = False
    observability_lines: list[int] = field(default_factory=list)
    has_eval_marker: bool = False
    mcp_transports: list[McpTransportFact] = field(default_factory=list)
    mcp_tools: list[McpToolFact] = field(default_factory=list)
    policy_prompts: list[PolicyPromptFact] = field(default_factory=list)
    inconclusive: list[InconclusiveFact] = field(default_factory=list)


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


def _assigned_names(node: ast.Assign | ast.AnnAssign) -> set[str]:
    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
    return {target.id for target in targets if isinstance(target, ast.Name)}


def _constant_text(node: ast.AST) -> str:
    values: list[str] = []
    for item in ast.walk(node):
        if not isinstance(item, ast.Constant):
            continue
        if isinstance(item.value, bytes):
            values.append(item.value.decode("utf-8", errors="ignore"))
        elif isinstance(item.value, str):
            values.append(item.value)
    return " ".join(values).lower()


def _strict_model_names(tree: ast.Module) -> set[str]:
    strict: set[str] = set()
    changed = True
    while changed:
        changed = False
        for node in tree.body:
            if not isinstance(node, ast.ClassDef) or node.name in strict:
                continue
            inherited = any(
                qualified_name(base).endswith("StrictModel") or qualified_name(base) in strict
                for base in node.bases
            )
            configured = any(
                isinstance(item, ast.Call)
                and qualified_name(item.func).endswith("ConfigDict")
                and any(
                    keyword.arg == "extra"
                    and isinstance(keyword.value, ast.Constant)
                    and keyword.value.value == "forbid"
                    for keyword in item.keywords
                )
                for item in ast.walk(node)
            )
            if inherited or configured:
                strict.add(node.name)
                changed = True
    return strict


def _auth_boundary_present(tree: ast.Module) -> bool:
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        text = _constant_text(node)
        calls = {
            qualified_name(item.func)
            for item in ast.walk(node)
            if isinstance(item, ast.Call)
        }
        statuses = {
            item.value
            for item in ast.walk(node)
            if isinstance(item, ast.Constant) and isinstance(item.value, int)
        }
        validates = any(name.endswith(("compare_digest", "decode")) for name in calls)
        if "authorization" in text and "bearer " in text and validates and statuses & {401, 403}:
            return True
    return False


def _handler_returns_generic_error(handler: ast.ExceptHandler) -> bool:
    returns = [item for item in ast.walk(handler) if isinstance(item, ast.Return)]
    if not returns:
        return False
    if len(returns) != 1:
        return False
    value = returns[0].value
    if not isinstance(value, (ast.Constant, ast.JoinedStr)):
        return False
    text = _constant_text(value)
    return any(word in text for word in ("error", "failed", "unable", "problem"))


def _function_has_structured_errors(function: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    text = _constant_text(function)
    return (
        any(token in text for token in ("iserror", "is_error"))
        and "category" in text
        and "retryable" in text
    )


def _function_has_policy_gate(function: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for item in ast.walk(function):
        if not isinstance(item, (ast.If, ast.Assert)):
            continue
        text = " ".join(
            qualified_name(candidate).lower()
            for candidate in ast.walk(item.test)
            if isinstance(candidate, (ast.Name, ast.Attribute))
        )
        if any(token in text for token in ("approval", "approved", "authorize", "identity", "authenticated")):
            return True
    return False


def _policy_prompt_facts(
    tree: ast.Module,
    functions: list[ast.FunctionDef | ast.AsyncFunctionDef],
) -> list[PolicyPromptFact]:
    destructive = [
        function
        for function in functions
        if function.name.lower().startswith(DESTRUCTIVE_PREFIXES)
        and any(
            isinstance(item, ast.Call) and _is_side_effect_call(qualified_name(item.func))
            for item in ast.walk(function)
        )
    ]
    if not destructive:
        return []
    module_enforcement = any(
        isinstance(item, ast.Call)
        and any(
            token in qualified_name(item.func).lower()
            for token in ("pretooluse", "pre_tool_use", "tool_choice", "approval", "authorize", "verify_identity")
        )
        for item in ast.walk(tree)
    ) or any(_function_has_policy_gate(function) for function in destructive)
    if module_enforcement:
        return []
    facts: list[PolicyPromptFact] = []
    for item in ast.walk(tree):
        if not isinstance(item, ast.Constant) or not isinstance(item.value, str):
            continue
        text = item.value.lower()
        ordered = any(token in text for token in ("before", "prior to", "only after"))
        gate = any(token in text for token in ("approval", "approve", "identity", "authenticate", "confirm"))
        action = any(token in text for token in ("delet", "destroy", "pay", "transfer", "send", "publish"))
        if ordered and gate and action:
            facts.append(
                PolicyPromptFact(
                    line=item.lineno,
                    detail="A critical ordering policy is stated in prompt text without recognized programmatic enforcement.",
                )
            )
    return facts


def _transport_is_guarded_stdio(tree: ast.Module, call: ast.Call) -> bool:
    """Recognize a local fail-closed guard before a dynamic FastMCP run call."""
    for function in ast.walk(tree):
        if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if call not in list(ast.walk(function)):
            continue
        for item in ast.walk(function):
            if not isinstance(item, ast.If) or item.lineno >= call.lineno:
                continue
            compared_to_stdio = any(
                isinstance(value, ast.Constant) and value.value == "stdio"
                for value in ast.walk(item.test)
            )
            rejects = any(isinstance(value, (ast.Raise, ast.Return)) for value in item.body)
            if compared_to_stdio and rejects:
                return True
    return False


def _mcp_facts(tree: ast.Module) -> tuple[
    list[McpTransportFact], list[McpToolFact], list[InconclusiveFact]
]:
    fastmcp_names: set[str] = set()
    authenticated_servers: set[str] = set()
    annotation_names: set[str] = set()
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)) or node.value is None:
            continue
        if not isinstance(node.value, ast.Call):
            continue
        call_name = qualified_name(node.value.func)
        names = _assigned_names(node)
        if call_name.endswith("FastMCP"):
            fastmcp_names.update(names)
            if any(
                keyword.arg in {"auth", "token_verifier", "auth_server_provider"}
                and not (
                    isinstance(keyword.value, ast.Constant)
                    and keyword.value.value is None
                )
                for keyword in node.value.keywords
            ):
                authenticated_servers.update(names)
        if call_name.endswith("ToolAnnotations"):
            annotation_names.update(names)
    strict_models = _strict_model_names(tree)
    hardened_servers = {
        item.args[0].id
        for item in ast.walk(tree)
        if isinstance(item, ast.Call)
        and qualified_name(item.func).endswith("_harden_tool_contracts")
        and item.args
        and isinstance(item.args[0], ast.Name)
    }
    auth_boundary = _auth_boundary_present(tree)
    functions = {
        item.name: item
        for item in ast.walk(tree)
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    transports: list[McpTransportFact] = []
    tools: list[McpToolFact] = []
    inconclusive: list[InconclusiveFact] = []
    for item in ast.walk(tree):
        if isinstance(item, ast.Call):
            call_name = qualified_name(item.func)
            receiver = call_name.rsplit(".", 1)[0]
            terminal = call_name.rsplit(".", 1)[-1]
            if terminal in {"streamable_http_app", "sse_app"}:
                transports.append(
                    McpTransportFact(
                        line=item.lineno,
                        authenticated=receiver in authenticated_servers or auth_boundary,
                        detail=f"MCP network application {terminal} is exposed.",
                    )
                )
            elif terminal == "run" and receiver in fastmcp_names:
                transport = next(
                    (keyword.value for keyword in item.keywords if keyword.arg == "transport"),
                    None,
                )
                if isinstance(transport, ast.Constant) and transport.value in {
                    "streamable-http",
                    "sse",
                }:
                    transports.append(
                        McpTransportFact(
                            line=item.lineno,
                            authenticated=receiver in authenticated_servers or auth_boundary,
                            detail=f"FastMCP runs with network transport {transport.value!r}.",
                        )
                    )
                elif transport is not None and not (
                    isinstance(transport, ast.Constant) and transport.value == "stdio"
                ):
                    if not _transport_is_guarded_stdio(tree, item):
                        inconclusive.append(
                            InconclusiveFact(
                                line=item.lineno,
                                code="AA014_INCONCLUSIVE_MCP_TRANSPORT",
                                detail="FastMCP transport is dynamically configured.",
                            )
                        )
            if terminal == "add_tool" and receiver in fastmcp_names and item.args:
                function = functions.get(qualified_name(item.args[0]))
                annotations = next(
                    (keyword.value for keyword in item.keywords if keyword.arg == "annotations"),
                    None,
                )
                has_annotations = (
                    isinstance(annotations, ast.Call)
                    and qualified_name(annotations.func).endswith("ToolAnnotations")
                ) or (isinstance(annotations, ast.Name) and annotations.id in annotation_names)
                if annotations is not None and not has_annotations:
                    inconclusive.append(
                        InconclusiveFact(
                            line=item.lineno,
                            code="AA015_INCONCLUSIVE_TOOL_ANNOTATIONS",
                            detail="Tool annotations are dynamically configured.",
                        )
                    )
                strict = receiver in hardened_servers or (
                    function is not None
                    and any(
                        isinstance(argument.annotation, ast.Name)
                        and argument.annotation.id in strict_models
                        for argument in function.args.args
                    )
                )
                if function is None:
                    inconclusive.append(
                        InconclusiveFact(
                            line=item.lineno,
                            code="AA016_INCONCLUSIVE_TOOL_MODEL",
                            detail="Registered tool function could not be resolved statically.",
                        )
                    )
                generic_error = bool(
                    function
                    and not _function_has_structured_errors(function)
                    and any(
                        _handler_returns_generic_error(handler)
                        for handler in (
                            candidate
                            for candidate in ast.walk(function)
                            if isinstance(candidate, ast.ExceptHandler)
                        )
                    )
                )
                tools.append(
                    McpToolFact(
                        line=item.lineno,
                        name=function.name if function is not None else qualified_name(item.args[0]),
                        has_annotations=has_annotations,
                        strict_arguments=strict,
                        generic_error=generic_error,
                    )
                )
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in item.decorator_list:
                decorator_call = decorator if isinstance(decorator, ast.Call) else None
                decorator_name = qualified_name(
                    decorator_call.func if decorator_call is not None else decorator
                )
                if not decorator_name.endswith(".tool"):
                    continue
                receiver = decorator_name.rsplit(".", 1)[0]
                if receiver not in fastmcp_names:
                    continue
                annotations = next(
                    (
                        keyword.value
                        for keyword in decorator_call.keywords
                        if keyword.arg == "annotations"
                    ),
                    None,
                ) if decorator_call is not None else None
                has_annotations = (
                    isinstance(annotations, ast.Call)
                    and qualified_name(annotations.func).endswith("ToolAnnotations")
                ) or (isinstance(annotations, ast.Name) and annotations.id in annotation_names)
                if annotations is not None and not has_annotations:
                    inconclusive.append(
                        InconclusiveFact(
                            line=item.lineno,
                            code="AA015_INCONCLUSIVE_TOOL_ANNOTATIONS",
                            detail="Tool annotations are dynamically configured.",
                        )
                    )
                strict = receiver in hardened_servers or any(
                    isinstance(argument.annotation, ast.Name)
                    and argument.annotation.id in strict_models
                    for argument in item.args.args
                )
                generic_error = not _function_has_structured_errors(item) and any(
                    _handler_returns_generic_error(handler)
                    for handler in (
                        candidate
                        for candidate in ast.walk(item)
                        if isinstance(candidate, ast.ExceptHandler)
                    )
                )
                tools.append(
                    McpToolFact(
                        line=item.lineno,
                        name=item.name,
                        has_annotations=has_annotations,
                        strict_arguments=strict,
                        generic_error=generic_error,
                    )
                )
    return transports, tools, inconclusive


def _function_has_validation(function: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    parameters = {argument.arg for argument in function.args.args}
    for node in ast.walk(function):
        expression: ast.AST | None = None
        if isinstance(node, (ast.If, ast.Assert)):
            expression = node.test
        elif isinstance(node, ast.Call) and qualified_name(node.func).endswith(
            ("model_validate", "validate_python")
        ):
            expression = node
        if expression is not None and any(
            isinstance(item, ast.Name) and item.id in parameters
            for item in ast.walk(expression)
        ):
            return True
    return False


def _call_uses_parameter(call: ast.Call, parameters: set[str]) -> bool:
    values = list(call.args) + [keyword.value for keyword in call.keywords]
    return any(
        isinstance(node, ast.Name) and node.id in parameters
        for value in values
        for node in ast.walk(value)
    )


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
    is_http_sink = call_name.startswith(("requests.", "httpx.", "aiohttp.")) and terminal in {
        "get",
        "post",
        "put",
        "patch",
        "delete",
        "request",
    }
    return (
        call_name == "open"
        or is_http_sink
        or terminal in SIDE_EFFECT_NAMES
        or terminal.startswith(DESTRUCTIVE_PREFIXES + ("save",))
    )


def _is_model_call(call: ast.Call) -> bool:
    name = qualified_name(call.func)
    return (
        ("responses." in name and name.rsplit(".", 1)[-1] in MODEL_METHODS)
        or name.endswith(("Runner.run", "Runner.run_sync", "Runner.run_streamed"))
    )


def _retry_evidence(scope: ast.AST) -> tuple[bool, bool]:
    retry = False
    backoff = False
    decorators = (
        scope.decorator_list
        if isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef))
        else []
    )
    for decorator in decorators:
        if isinstance(decorator, ast.Call) and qualified_name(decorator.func).endswith(
            ("retry", "tenacity.retry")
        ):
            retry = True
            for keyword in decorator.keywords:
                if keyword.arg == "wait" and any(
                    isinstance(item, ast.Call)
                    and qualified_name(item.func).endswith(
                        ("wait_exponential", "wait_random_exponential")
                    )
                    for item in ast.walk(keyword.value)
                ):
                    backoff = True
    for item in ast.walk(scope):
        if not isinstance(item, ast.Call):
            continue
        name = qualified_name(item.func)
        if name.endswith(("wait_exponential", "wait_random_exponential")):
            retry = True
            backoff = True
        if name.endswith(("sleep", "asyncio.sleep", "time.sleep")) and item.args:
            if any(isinstance(part, (ast.Mult, ast.Pow)) for part in ast.walk(item.args[0])):
                retry = True
                backoff = True
    return retry, backoff


def _walk_scope(scope: ast.AST):  # type: ignore[no-untyped-def]
    stack = [scope]
    while stack:
        item = stack.pop()
        yield item
        children = list(ast.iter_child_nodes(item))
        if item is not scope and isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            continue
        stack.extend(reversed(children))


def _proven_collections(scope: ast.AST) -> tuple[set[str], set[str]]:
    proven: set[str] = set()
    bounded: set[str] = set()
    for item in _walk_scope(scope):
        if not isinstance(item, (ast.Assign, ast.AnnAssign)) or item.value is None:
            continue
        targets = item.targets if isinstance(item, ast.Assign) else [item.target]
        names = {target.id for target in targets if isinstance(target, ast.Name)}
        value = item.value
        is_list = isinstance(value, ast.List) or (
            isinstance(value, ast.Call) and qualified_name(value.func) == "list"
        )
        is_deque = isinstance(value, ast.Call) and qualified_name(value.func).endswith("deque")
        if is_list or is_deque:
            proven.update(names)
        if isinstance(value, ast.Call) and is_deque and any(
            keyword.arg == "maxlen" for keyword in value.keywords
        ):
            bounded.update(names)
    return proven, bounded


def _slice_of_name(node: ast.AST, name: str) -> bool:
    return (
        isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Name)
        and node.value.id == name
        and isinstance(node.slice, ast.Slice)
    )


def _tail_slice_of_name(node: ast.AST, name: str) -> bool:
    if (
        not _slice_of_name(node, name)
        or not isinstance(node, ast.Subscript)
        or not isinstance(node.slice, ast.Slice)
    ):
        return False
    lower = node.slice.lower
    return (
        isinstance(lower, ast.UnaryOp)
        and isinstance(lower.op, ast.USub)
        and isinstance(lower.operand, (ast.Constant, ast.Name))
    )


def _has_truncation(scope: ast.AST, name: str, bounded: set[str]) -> bool:
    if name in bounded:
        return True
    for item in _walk_scope(scope):
        if isinstance(item, (ast.Assign, ast.AnnAssign)) and item.value is not None:
            targets = item.targets if isinstance(item, ast.Assign) else [item.target]
            if any(
                (isinstance(target, ast.Name) and target.id == name)
                or _slice_of_name(target, name)
                for target in targets
            ) and _tail_slice_of_name(item.value, name):
                return True
        if isinstance(item, ast.Delete) and any(_slice_of_name(target, name) for target in item.targets):
            return True
        if isinstance(item, ast.Call) and isinstance(item.func, ast.Attribute):
            if isinstance(item.func.value, ast.Name) and item.func.value.id == name:
                if item.func.attr == "popleft" or (
                    item.func.attr == "pop"
                    and item.args
                    and isinstance(item.args[0], ast.Constant)
                    and item.args[0].value == 0
                ):
                    return True
    return False


def _context_growth_facts(tree: ast.Module) -> tuple[list[ContextGrowthFact], list[int]]:
    findings: list[ContextGrowthFact] = []
    inconclusive: set[int] = set()
    functions = [item for item in ast.walk(tree) if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))]
    for loop in [item for item in ast.walk(tree) if isinstance(item, (ast.For, ast.AsyncFor, ast.While))]:
        scope = min(
            (
                function
                for function in functions
                if function.lineno <= loop.lineno <= (function.end_lineno or function.lineno)
            ),
            key=lambda function: (function.end_lineno or function.lineno) - function.lineno,
            default=tree,
        )
        proven, bounded = _proven_collections(scope)
        loop_nodes = list(_walk_scope(loop))
        appended = {
            item.func.value.id
            for item in loop_nodes
            if isinstance(item, ast.Call)
            and isinstance(item.func, ast.Attribute)
            and item.func.attr == "append"
            and isinstance(item.func.value, ast.Name)
        }
        model_calls = [item for item in loop_nodes if isinstance(item, ast.Call) and _is_model_call(item)]
        if not appended or not model_calls:
            continue
        matched = False
        for call in model_calls:
            for keyword in call.keywords:
                if keyword.arg not in {"messages", "input", "history"} or not isinstance(keyword.value, ast.Name):
                    continue
                name = keyword.value.id
                if name not in appended:
                    continue
                matched = True
                if name not in proven:
                    inconclusive.add(loop.lineno)
                elif not _has_truncation(scope, name, bounded):
                    findings.append(
                        ContextGrowthFact(
                            line=loop.lineno,
                            collection=name,
                            detail=f"{name} is appended and reused as {keyword.arg} inside the loop without recognized truncation.",
                        )
                    )
        if not matched:
            inconclusive.add(loop.lineno)
    unique = {(item.line, item.collection): item for item in findings}
    return list(unique.values()), sorted(inconclusive)


def analyze_source(tree: ast.Module, source: str) -> FileFacts:
    facts = FileFacts()
    facts.mcp_transports, facts.mcp_tools, facts.inconclusive = _mcp_facts(tree)
    functions = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    facts.policy_prompts = _policy_prompt_facts(tree, functions)
    if facts.mcp_transports or facts.mcp_tools:
        facts.agent_present = True
        lines = [item.line for item in facts.mcp_transports]
        lines.extend(item.line for item in facts.mcp_tools)
        facts.first_agent_line = min(lines)
    facts.context_growth, facts.context_growth_inconclusive = _context_growth_facts(tree)
    budget_names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        budget_names.update(
            target.id
            for target in targets
            if isinstance(target, ast.Name) and "budget" in target.id.lower()
        )
    facts.has_run_budget = any(
        isinstance(node, ast.If)
        and any(
            (
                isinstance(item, ast.Name)
                and (item.id in budget_names or "budget" in item.id.lower())
            )
            or (isinstance(item, ast.Attribute) and "budget" in item.attr.lower())
            for item in ast.walk(node.test)
        )
        for node in ast.walk(tree)
    )
    facts.has_eval_marker = "uptocode: eval agent" in source
    client_timeout = False
    client_retry = False
    client_backoff = False
    configured_clients: dict[str, tuple[bool, bool, bool]] = {}
    environment_secrets: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        value = node.value
        if value is None:
            continue
        is_environment = isinstance(value, ast.Subscript) and qualified_name(value.value).endswith("os.environ")
        is_getenv = isinstance(value, ast.Call) and qualified_name(value.func).endswith(("os.getenv", "getenv"))
        if not (is_environment or is_getenv):
            option_call = next(
                (
                    item
                    for item in ast.walk(value)
                    if isinstance(item, ast.Call)
                    and qualified_name(item.func).endswith("with_options")
                ),
                None,
            )
            if option_call is not None:
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                names = [target.id for target in targets if isinstance(target, ast.Name)]
                has_timeout = any(keyword.arg == "timeout" for keyword in option_call.keywords)
                has_retry = any(keyword.arg == "max_retries" for keyword in option_call.keywords)
                has_backoff = has_retry
                for name in names:
                    configured_clients[name] = (has_timeout, has_retry, has_backoff)
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        environment_secrets.update(target.id for target in targets if isinstance(target, ast.Name))

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            call_name = qualified_name(node.func)
            terminal_name = call_name.rsplit(".", 1)[-1]
            if (
                terminal_name in {"debug", "info", "warning", "error", "exception", "critical", "trace", "start_span"}
                or "tracing" in call_name
            ):
                facts.observability_lines.append(node.lineno)
            if call_name.endswith("OpenAI"):
                client_timeout |= any(keyword.arg == "timeout" for keyword in node.keywords)
                has_builtin_retry = any(keyword.arg == "max_retries" for keyword in node.keywords)
                client_retry |= has_builtin_retry or any(keyword.arg == "retry" for keyword in node.keywords)
                client_backoff |= has_builtin_retry
            is_agent = call_name.endswith("Agent") or "Runner.run" in call_name
            is_model = "responses." in call_name and call_name.rsplit(".", 1)[-1] in MODEL_METHODS
            if is_agent or is_model:
                facts.agent_present = True
                facts.first_agent_line = min(facts.first_agent_line, node.lineno) if facts.first_agent_line != 1 else node.lineno
            if is_model:
                root_name = call_name.split(".", 1)[0]
                configured_timeout, configured_retry, configured_backoff = configured_clients.get(
                    root_name, (False, False, False)
                )
                enclosing = min(
                    (
                        scope
                        for scope in ast.walk(tree)
                        if isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and scope.lineno <= node.lineno <= (scope.end_lineno or scope.lineno)
                    ),
                    key=lambda scope: (scope.end_lineno or scope.lineno) - scope.lineno,
                    default=tree,
                )
                scope_retry, scope_backoff = _retry_evidence(enclosing)
                for keyword in node.keywords:
                    if keyword.arg not in {"input", "prompt", "messages"}:
                        continue
                    if any(isinstance(candidate, ast.Name) and candidate.id in environment_secrets for candidate in ast.walk(keyword.value)):
                        facts.secret_prompt_exposures.append(node.lineno)
                facts.model_calls.append(
                    ModelCallFact(
                        line=node.lineno,
                        has_output_limit=any(keyword.arg in {"max_output_tokens", "max_tokens"} for keyword in node.keywords),
                        has_timeout=client_timeout or configured_timeout or any(keyword.arg == "timeout" for keyword in node.keywords),
                        has_retry=client_retry or configured_retry or scope_retry or any(keyword.arg in {"retry", "max_retries"} for keyword in node.keywords),
                        has_backoff=client_backoff or configured_backoff or scope_backoff or any(keyword.arg == "max_retries" for keyword in node.keywords),
                    )
                )
            terminal = call_name.rsplit(".", 1)[-1]
            if _is_side_effect_call(call_name) and _contains_raw_model_output(node) and not _contains_validation(node):
                facts.raw_output_sinks.append(SinkFact(node.lineno, terminal))
            parameterized_sql = terminal == "execute" and len(node.args) >= 2
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value.startswith("sk-") and len(node.value) >= 20:
                facts.hardcoded_secrets.append(node.lineno)
            if contains_pii(node.value):
                facts.hardcoded_pii.append(node.lineno)

    for function in functions:
        is_tool = _is_tool(function)
        if is_tool:
            facts.agent_present = True
        parameters = {argument.arg for argument in function.args.args}
        validation = _function_has_validation(function)
        destructive_name = function.name.lower().startswith(DESTRUCTIVE_PREFIXES)
        has_side_effect = False
        argument_risk = False
        for candidate in ast.walk(function):
            if not isinstance(candidate, ast.Call):
                continue
            call_name = qualified_name(candidate.func)
            terminal = call_name.rsplit(".", 1)[-1]
            if _is_side_effect_call(call_name):
                has_side_effect = True
                parameterized_sql = terminal == "execute" and len(candidate.args) >= 2
                if (
                    is_tool
                    and _call_uses_parameter(candidate, parameters)
                    and not validation
                    and not parameterized_sql
                ):
                    argument_risk = True
                    facts.risky_sinks.append(SinkFact(candidate.lineno, terminal))
        if is_tool:
            facts.tools.append(
                ToolFact(
                    line=function.lineno,
                    name=function.name,
                    destructive=destructive_name and has_side_effect,
                    approval=any(_decorator_approval(item) for item in function.decorator_list),
                    argument_risk=argument_risk,
                )
            )
    facts.has_observability = bool(facts.observability_lines)
    return facts
