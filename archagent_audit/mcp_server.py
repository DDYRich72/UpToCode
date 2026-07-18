"""Static-first MCP tools for editor and agent integrations."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from archagent_audit.adapters.python import extract_python_evidence
from archagent_audit.engine import scan_path
from archagent_audit.redaction import redact_text
from archagent_audit.rules.aa001 import evaluate_aa001
from archagent_audit.rules.registry import load_core_rules


server = FastMCP(
    "ArchAgent",
    instructions=(
        "Architecture-quality analysis for Python agent code. Tools are static-only "
        "unless judgment and send_code are both explicitly true."
    ),
)


def _scan_source(
    source: str,
    *,
    filename: str = "snippet.py",
    judgment: bool = False,
    send_code: bool = False,
) -> dict[str, Any]:
    if judgment and not send_code:
        raise ValueError("judgment=true requires send_code=true")
    with tempfile.TemporaryDirectory(prefix="archagent-audit-") as directory:
        path = Path(directory) / filename
        path.write_text(source, encoding="utf-8")
        report = scan_path(
            directory,
            judgment=judgment,
            send_code=send_code,
        )
    report.scan_root = "<submitted-code>"
    return report.model_dump(mode="json")


@server.tool()
def audit_file(
    path: str,
    judgment: bool = False,
    send_code: bool = False,
) -> dict[str, Any]:
    """Audit one local Python file; judgment requires explicit code-sharing consent."""
    source_path = Path(path).resolve()
    if not source_path.is_file() or source_path.suffix.lower() != ".py":
        raise ValueError(f"Python file not found: {source_path}")
    try:
        source = source_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(f"Python file is not UTF-8: {source_path}") from error
    return _scan_source(
        source,
        filename=source_path.name,
        judgment=judgment,
        send_code=send_code,
    )


def _added_python(diff: str) -> str:
    lines = []
    for line in diff.splitlines():
        if line.startswith("+++"):
            continue
        if line.startswith("+"):
            lines.append(line[1:])
    return "\n".join(lines) + ("\n" if lines else "")


@server.tool()
def audit_diff(
    diff: str,
    judgment: bool = False,
    send_code: bool = False,
) -> dict[str, Any]:
    """Audit added Python lines from a unified diff without modifying the repository."""
    return _scan_source(
        _added_python(diff),
        filename="diff.py",
        judgment=judgment,
        send_code=send_code,
    )


@server.tool()
def check_tool_schema(
    schema_json: str,
    judgment: bool = False,
    send_code: bool = False,
) -> dict[str, Any]:
    """Validate the minimum deterministic contract of a function-tool schema."""
    if judgment and not send_code:
        raise ValueError("judgment=true requires send_code=true")
    try:
        schema = json.loads(schema_json)
    except json.JSONDecodeError as error:
        return {"valid": False, "issues": [{"field": "$", "message": str(error)}]}
    if not isinstance(schema, dict):
        return {
            "valid": False,
            "issues": [{"field": "$", "message": "Schema must be a JSON object."}],
        }
    issues = []
    for field in ("name", "description", "inputSchema"):
        if not schema.get(field):
            issues.append({"field": field, "message": f"Missing non-empty {field}."})
    input_schema = schema.get("inputSchema")
    if isinstance(input_schema, dict) and input_schema.get("type") != "object":
        issues.append(
            {"field": "inputSchema.type", "message": "Tool input schema must be an object."}
        )
    return {
        "valid": not issues,
        "issues": issues,
        "judgment_status": "not-requested" if not judgment else "not-applicable",
    }


@server.tool()
def check_loop(snippet: str) -> dict[str, Any]:
    """Check a Python loop or Runner invocation for AA001."""
    redacted, counts = redact_text(snippet)
    try:
        evidence = extract_python_evidence(redacted)
    except SyntaxError as error:
        return {
            "findings": [],
            "analysis_warnings": [
                {
                    "code": "PYTHON_PARSE_ERROR",
                    "message": "Python snippet could not be parsed.",
                    "line": error.lineno,
                }
            ],
            "redactions": counts.model_dump(),
        }
    lines = redacted.splitlines()
    findings = []
    warnings = []
    for loop in evidence.loops:
        excerpt = "\n".join(lines[max(0, loop.line - 2): min(len(lines), loop.line + 1)])
        finding, warning = evaluate_aa001(loop, file="snippet.py", excerpt=excerpt)
        if finding:
            findings.append(finding.model_dump(mode="json"))
        if warning:
            warnings.append(warning.model_dump(mode="json"))
    return {
        "findings": findings,
        "analysis_warnings": warnings,
        "redactions": counts.model_dump(),
    }


@server.tool()
def get_rule(rule_id: str) -> dict[str, Any]:
    """Return one rule's metadata and direct primary-source URLs."""
    normalized = rule_id.upper()
    for definition in load_core_rules():
        if definition.id == normalized:
            return {
                "id": definition.id,
                "name": definition.name,
                "tier": definition.tier,
                "severity": definition.severity.value,
                "citations": [str(url).rstrip("/") for url in definition.citations],
            }
    return {
        "error": {
            "code": "RULE_NOT_FOUND",
            "message": f"Unknown ArchAgent rule: {normalized}",
        }
    }


def run_server() -> None:
    """Run the MCP server over stdio."""
    server.run(transport="stdio")


if __name__ == "__main__":
    run_server()
