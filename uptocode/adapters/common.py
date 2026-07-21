"""Shared AST helpers for Python framework adapters."""

from __future__ import annotations

import ast


DESTRUCTIVE_PREFIXES = ("delete", "remove", "send", "pay", "write", "update", "create")


def qualified_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = qualified_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    if isinstance(node, ast.Call):
        return qualified_name(node.func)
    return ""


def keyword(call: ast.Call, name: str) -> ast.AST | None:
    return next((item.value for item in call.keywords if item.arg == name), None)


def literal(node: ast.AST | None) -> object:
    return node.value if isinstance(node, ast.Constant) else None


def contains_exit(node: ast.AST) -> bool:
    if isinstance(node, (ast.Break, ast.Return, ast.Raise)):
        return True
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
        return False
    return any(contains_exit(child) for child in ast.iter_child_nodes(node))


def function_is_destructive(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    lowered = node.name.lower()
    if lowered.startswith(DESTRUCTIVE_PREFIXES):
        return True
    for candidate in ast.walk(node):
        if not isinstance(candidate, ast.Call):
            continue
        terminal = qualified_name(candidate.func).rsplit(".", 1)[-1].lower()
        if terminal.startswith(DESTRUCTIVE_PREFIXES):
            return True
    return False


def function_has_validation(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    parameters = {argument.arg for argument in node.args.args}
    for candidate in ast.walk(node):
        expression: ast.AST | None = None
        if isinstance(candidate, (ast.If, ast.Assert)):
            expression = candidate.test
        elif isinstance(candidate, ast.Call) and qualified_name(candidate.func).endswith(
            ("model_validate", "validate_python")
        ):
            expression = candidate
        if expression is not None and any(
            isinstance(item, ast.Name) and item.id in parameters for item in ast.walk(expression)
        ):
            return True
    return False


def assigned_calls(tree: ast.AST) -> dict[str, ast.Call]:
    result: dict[str, ast.Call] = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)) or node.value is None:
            continue
        if not isinstance(node.value, ast.Call):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        for target in targets:
            if isinstance(target, ast.Name):
                result[target.id] = node.value
    return result
