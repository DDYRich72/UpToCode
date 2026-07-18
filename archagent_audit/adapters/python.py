"""Python AST evidence extraction used by the Gate 1 AA001 slice."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field

from archagent_audit.models import AnalysisWarning


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
        prefix = _qualified_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def _has_break(node: ast.While) -> bool:
    return any(isinstance(candidate, ast.Break) for candidate in ast.walk(node))


class EvidenceVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.result = PythonEvidence()

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
            else:
                kind, detail = "unknown", "max_turns is dynamically configured"
            self.result.loops.append(LoopEvidence(node.lineno, "openai-agents", kind, detail))
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:  # noqa: N802
        if isinstance(node.test, ast.Constant) and node.test.value is True:
            self.result.frameworks.add("custom-python")
            kind = "custom" if _has_break(node) else "disabled"
            detail = "loop contains an exit" if kind == "custom" else "while True has no exit"
            self.result.loops.append(LoopEvidence(node.lineno, "custom-python", kind, detail))
        self.generic_visit(node)


def extract_python_evidence(source: str) -> PythonEvidence:
    tree = ast.parse(source)
    visitor = EvidenceVisitor()
    visitor.visit(tree)
    return visitor.result

