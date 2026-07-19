"""Conservative candidate extraction for rules that require model judgment."""

from __future__ import annotations

import ast
from dataclasses import dataclass

from archagent_audit.analysis import DESTRUCTIVE_PREFIXES, SIDE_EFFECT_NAMES, qualified_name


@dataclass(frozen=True)
class JudgmentCandidate:
    rule_id: str
    file: str
    line: int
    evidence: str
    excerpt: str


def _excerpt(lines: list[str], line: int) -> str:
    return "\n".join(lines[max(0, line - 2): min(len(lines), line + 1)])


def _contains_raw_model_output(node: ast.AST) -> bool:
    return any(
        isinstance(item, ast.Attribute)
        and item.attr in {"output_text", "content", "final_output"}
        for item in ast.walk(node)
    )


def _contains_validation(node: ast.AST) -> bool:
    return any(
        isinstance(item, ast.Call)
        and qualified_name(item.func).endswith(
            ("model_validate", "parse_obj", "validate_python")
        )
        for item in ast.walk(node)
    )


def collect_judgment_candidates(
    sources: list[tuple[str, str]],
) -> list[JudgmentCandidate]:
    candidates: list[JudgmentCandidate] = []
    agent_locations: list[tuple[str, int, list[str]]] = []
    has_eval = any(
        "archagent-audit: eval agent" in source
        or (
            file.rsplit("/", 1)[-1].startswith("test_")
            and any(
                token in source
                for token in ("Runner.run", "run_agent(", "agent.run(", "Agent(")
            )
        )
        for file, source in sources
    )
    for file, source in sources:
        tree = ast.parse(source)
        lines = source.splitlines()
        external_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                call = qualified_name(node.value.func)
                if call.startswith(("requests.", "httpx.")) or call in {"open", "Path.read_text"}:
                    external_names.update(target.id for target in node.targets if isinstance(target, ast.Name))
            if isinstance(node, ast.Call) and qualified_name(node.func).endswith("Agent"):
                agent_locations.append((file, node.lineno, lines))
            if isinstance(node, ast.Call) and "responses." in qualified_name(node.func):
                for keyword in node.keywords:
                    if keyword.arg in {"input", "prompt", "messages"} and any(
                        isinstance(candidate, ast.Name) and candidate.id in external_names
                        for candidate in ast.walk(keyword.value)
                    ):
                        candidates.append(JudgmentCandidate("AA005", file, node.lineno, "External content flows directly to a model input.", _excerpt(lines, node.lineno)))
            if isinstance(node, ast.Call):
                terminal = qualified_name(node.func).rsplit(".", 1)[-1].lower()
                if (
                    terminal in SIDE_EFFECT_NAMES
                    and _contains_raw_model_output(node)
                    and not _contains_validation(node)
                ):
                    candidates.append(
                        JudgmentCandidate(
                            "AA010",
                            file,
                            node.lineno,
                            "Raw model output reaches a write-like operation without recognized validation.",
                            _excerpt(lines, node.lineno),
                        )
                    )
        for function in [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]:
            is_tool = any("function_tool" in qualified_name(item.func if isinstance(item, ast.Call) else item) for item in function.decorator_list)
            if not is_tool:
                continue
            candidates.append(JudgmentCandidate("AA009", file, function.lineno, "Tool schema requires semantic quality review.", _excerpt(lines, function.lineno)))
            ambiguous_name = not function.name.lower().startswith(DESTRUCTIVE_PREFIXES)
            writes = any(
                isinstance(node, ast.Call)
                and qualified_name(node.func).rsplit(".", 1)[-1] in {"write", "execute", "save", "update"}
                for node in ast.walk(function)
            )
            if ambiguous_name and writes:
                candidates.append(JudgmentCandidate("AA003", file, function.lineno, "Ambiguously named tool contains a write-like operation.", _excerpt(lines, function.lineno)))
    if len(agent_locations) > 1:
        file, line, lines = agent_locations[0]
        candidates.append(JudgmentCandidate("AA008", file, line, f"Repository defines {len(agent_locations)} agents.", _excerpt(lines, line)))
    if agent_locations and not has_eval:
        file, line, lines = agent_locations[0]
        candidates.append(JudgmentCandidate("AA011", file, line, "Agent code has no recognized eval artifact.", _excerpt(lines, line)))
    return sorted(candidates, key=lambda item: (item.rule_id, item.file, item.line))
