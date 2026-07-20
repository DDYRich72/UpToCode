"""Python AST evidence extraction used by the Gate 1 AA001 slice."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field

from uptocode.models import AnalysisWarning


@dataclass(frozen=True)
class LoopEvidence:
    line: int
    framework: str
    bound_kind: str
    detail: str


@dataclass
class PythonEvidence:
    loops: list[LoopEvidence] = field(default_factory=list)
    warnings: list[AnalysisWarning] = field(default_factory=list)
    frameworks: set[str] = field(default_factory=set)


def _qualified_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        if (
            isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id == "super"
        ):
            return f"super.{node.attr}"
        prefix = _qualified_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def _contains_exit(node: ast.AST) -> bool:
    if isinstance(node, (ast.Break, ast.Return, ast.Raise)):
        return True
    if isinstance(node, (ast.For, ast.AsyncFor, ast.While, ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
        return False
    return any(_contains_exit(child) for child in ast.iter_child_nodes(node))


def _has_loop_exit(node: ast.While) -> bool:
    return any(_contains_exit(statement) for statement in node.body)


def _has_recursive_base_case(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for candidate in ast.walk(node):
        if not isinstance(candidate, ast.If):
            continue
        branch_has_exit = any(_contains_exit(statement) for statement in candidate.body)
        branch_recurses = any(
            isinstance(item, ast.Call) and _qualified_name(item.func) == node.name
            for item in ast.walk(candidate)
        )
        if branch_has_exit and not branch_recurses:
            return True
    return False


class EvidenceVisitor(ast.NodeVisitor):
    def __init__(self, constants: dict[str, int | None]) -> None:
        self.result = PythonEvidence()
        self.constants = constants

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        name = _qualified_name(node.func)
        if name.endswith("Runner.run") or name.endswith("Runner.run_sync") or name.endswith(
            "Runner.run_streamed"
        ):
            self.result.frameworks.add("openai-agents")
            max_turns = next(
                (keyword.value for keyword in node.keywords if keyword.arg == "max_turns"),
                None,
            )
            has_keyword = any(keyword.arg == "max_turns" for keyword in node.keywords)
            if not has_keyword:
                kind, detail = "sdk-default", "OpenAI Agents SDK bounded default"
            elif isinstance(max_turns, ast.Constant) and max_turns.value is None:
                kind, detail = "disabled", "max_turns=None"
            elif isinstance(max_turns, ast.Constant) and isinstance(max_turns.value, int):
                kind, detail = "explicit", f"max_turns={max_turns.value}"
            elif isinstance(max_turns, ast.Name) and max_turns.id in self.constants:
                value = self.constants[max_turns.id]
                kind = "disabled" if value is None else "explicit"
                detail = f"max_turns={value!r} via {max_turns.id}"
            else:
                kind, detail = "unknown", "max_turns is dynamically configured"
            self.result.loops.append(LoopEvidence(node.lineno, "openai-agents", kind, detail))
        elif name.endswith((".invoke", ".ainvoke")):
            config = next((keyword.value for keyword in node.keywords if keyword.arg == "config"), None)
            if isinstance(config, ast.Dict):
                for key, recursion_value in zip(config.keys, config.values, strict=False):
                    if not isinstance(key, ast.Constant) or key.value != "recursion_limit":
                        continue
                    self.result.frameworks.add("langgraph")
                    if isinstance(recursion_value, ast.Constant) and recursion_value.value is None:
                        kind, detail = "disabled", "recursion_limit=None"
                    elif isinstance(recursion_value, ast.Constant) and isinstance(
                        recursion_value.value, int
                    ):
                        kind, detail = "explicit", f"recursion_limit={recursion_value.value}"
                    else:
                        kind, detail = "unknown", "recursion_limit is dynamically configured"
                    self.result.loops.append(LoopEvidence(node.lineno, "langgraph", kind, detail))
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:  # noqa: N802
        if isinstance(node.test, ast.Constant) and node.test.value is True:
            self.result.frameworks.add("custom-python")
            kind = "custom" if _has_loop_exit(node) else "disabled"
            detail = "loop contains an exit" if kind == "custom" else "while True has no exit"
            self.result.loops.append(LoopEvidence(node.lineno, "custom-python", kind, detail))
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        recursive = any(
            isinstance(candidate, ast.Call)
            and _qualified_name(candidate.func) in {
                node.name,
                f"self.{node.name}",
                f"cls.{node.name}",
            }
            for candidate in ast.walk(node)
        )
        has_base_case = _has_recursive_base_case(node)
        if recursive:
            self.result.frameworks.add("custom-python")
            kind = "custom" if has_base_case else "disabled"
            detail = "recursive function has a base case" if has_base_case else "direct recursion has no base case"
            self.result.loops.append(LoopEvidence(node.lineno, "custom-python", kind, detail))
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        recursive = any(
            isinstance(candidate, ast.Call)
            and _qualified_name(candidate.func)
            in {node.name, f"self.{node.name}", f"cls.{node.name}"}
            for candidate in ast.walk(node)
        )
        has_base_case = _has_recursive_base_case(node)
        if recursive:
            self.result.frameworks.add("custom-python")
            kind = "custom" if has_base_case else "disabled"
            detail = (
                "recursive function has a base case"
                if has_base_case
                else "direct recursion has no base case"
            )
            self.result.loops.append(LoopEvidence(node.lineno, "custom-python", kind, detail))
        self.generic_visit(node)


def extract_python_evidence(source: str) -> PythonEvidence:
    tree = ast.parse(source)
    constants: dict[str, int | None] = {}
    for statement in tree.body:
        if not isinstance(statement, (ast.Assign, ast.AnnAssign)):
            continue
        value = statement.value
        if not isinstance(value, ast.Constant) or not (
            value.value is None or isinstance(value.value, int)
        ):
            continue
        targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
        for target in targets:
            if isinstance(target, ast.Name):
                constants[target.id] = value.value
    visitor = EvidenceVisitor(constants)
    visitor.visit(tree)
    return visitor.result
