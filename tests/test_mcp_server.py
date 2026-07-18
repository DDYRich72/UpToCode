from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from archagent_audit.mcp_server import (
    audit_diff,
    audit_file,
    check_loop,
    check_tool_schema,
    get_rule,
    server,
)


def test_mcp_exposes_the_five_committed_tools() -> None:
    tools = asyncio.run(server.list_tools())

    assert {tool.name for tool in tools} == {
        "audit_file",
        "audit_diff",
        "check_tool_schema",
        "check_loop",
        "get_rule",
    }


def test_check_loop_and_audit_diff_detect_aa001() -> None:
    loop_result = check_loop("while True:\n    work()\n")
    diff_result = audit_diff("diff --git a/a.py b/a.py\n+++ b/a.py\n@@ -0,0 +1,2 @@\n+while True:\n+    work()\n")

    assert "AA001" in {item["rule_id"] for item in loop_result["findings"]}
    assert "AA001" in {item["rule_id"] for item in diff_result["findings"]}


def test_static_only_default_and_code_sharing_consent(tmp_path: Path) -> None:
    source = tmp_path / "agent.py"
    source.write_text("while True:\n    work()\n", encoding="utf-8")

    result = audit_file(str(source))

    assert result["judgment_status"] == "not-requested"
    with pytest.raises(ValueError, match="send_code"):
        audit_file(str(source), judgment=True)


def test_tool_schema_reports_specific_contract_gaps() -> None:
    result = check_tool_schema(json.dumps({"name": "do"}))

    assert result["valid"] is False
    assert {item["field"] for item in result["issues"]} == {"description", "inputSchema"}


def test_get_rule_returns_primary_urls_and_unknown_is_structured() -> None:
    found = get_rule("AA001")
    missing = get_rule("AA999")

    assert found["id"] == "AA001"
    assert all(url.startswith("https://") for url in found["citations"])
    assert missing["error"]["code"] == "RULE_NOT_FOUND"


def test_malformed_mcp_call_does_not_kill_server() -> None:
    async def exercise() -> None:
        with pytest.raises(Exception):
            await server.call_tool("check_loop", {"wrong": "value"})
        content = await server.call_tool(
            "check_loop",
            {"snippet": "while True:\n    work()\n"},
        )
        assert content

    asyncio.run(exercise())
