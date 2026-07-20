from __future__ import annotations

import asyncio
import ast
import hashlib
import json
import socket
from pathlib import Path

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from uptocode.baseline import apply_baseline, create_baseline
from uptocode.config import ScanConfig, load_config
from uptocode.cli import app
from uptocode.diffing import DiffReconstructionError, reconstruct_unified_diff
from uptocode.engine import AuditService, scan_path
from uptocode.fingerprints import finding_fingerprint
from uptocode.mcp_server import (
    MAX_SOURCE_BYTES,
    _workspace_diff_bases,
    BearerKeyMiddleware,
    TokenBucketLimiter,
    audit_file,
    audit_source,
    create_server,
    hosted_app,
)
from uptocode.models import Report
from uptocode.reporters.sarif import render_sarif
from uptocode.review import create_manifest
from uptocode.rules.plugins import RuleContext, evaluate_plugins, load_rule_plugins
from uptocode.schema_validation import validate_tool_schema


def test_content_fingerprint_is_location_independent() -> None:
    first = finding_fingerprint(
        "AA001", "agent.py", "custom-loop-no-exit", excerpt="while True:\n    work()"
    )
    after_insert = finding_fingerprint(
        "AA001", "agent.py", "custom-loop-no-exit", excerpt="while True:\n    work()"
    )

    assert first == after_insert
    assert len(first) == 24


def test_super_init_is_not_direct_recursion(tmp_path: Path) -> None:
    source = tmp_path / "errors.py"
    source.write_text(
        "class DomainError(ValueError):\n"
        "    def __init__(self, message: str) -> None:\n"
        "        super().__init__(message)\n",
        encoding="utf-8",
    )

    report = scan_path(source)

    assert not [item for item in report.findings if item.rule_id == "AA001"]


def test_modified_diff_requires_and_uses_matching_base() -> None:
    diff = "--- a.py\n+++ a.py\n@@ -1,2 +1,2 @@\n value = 1\n-print(value)\n+print(value + 1)\n"

    with pytest.raises(DiffReconstructionError) as caught:
        reconstruct_unified_diff(diff)
    assert caught.value.code == "DIFF_CONTEXT_REQUIRED"

    result = reconstruct_unified_diff(
        diff,
        base_files={"a.py": "value = 1\nprint(value)\n"},
    )
    assert result[0].source == "value = 1\nprint(value + 1)\n"


def test_schema_validation_is_draft_2020_12_and_strict() -> None:
    valid = validate_tool_schema(
        {
            "name": "audit_source",
            "description": "Audit one submitted Python source document.",
            "inputSchema": {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "Python source to audit."}
                },
                "required": ["source"],
                "additionalProperties": False,
            },
        }
    )
    loose = validate_tool_schema(
        {
            "name": "audit_source",
            "description": "Audit one submitted Python source document.",
            "inputSchema": {"type": "object"},
        }
    )

    assert valid.valid is True
    assert loose.valid is False


def test_schema_validation_rejects_non_objects_and_invalid_drafts() -> None:
    assert validate_tool_schema("not an object").valid is False
    result = validate_tool_schema(
        {
            "name": "bad name",
            "description": "A deliberately invalid strict tool descriptor.",
            "inputSchema": {
                "type": "object",
                "properties": {"value": {"type": "unknown"}},
                "additionalProperties": False,
            },
        }
    )
    assert result.valid is False
    assert {issue.field for issue in result.issues} >= {"name", "inputSchema"}


def test_baseline_and_sarif_share_report_2_contract(tmp_path: Path) -> None:
    source = tmp_path / "loop.py"
    source.write_text("while True:\n    work()\n", encoding="utf-8")
    report = scan_path(source)
    baseline = create_baseline(report)
    sarif = json.loads(render_sarif(report))

    report, existing = apply_baseline(report, baseline)

    assert existing
    assert report.findings == []
    assert report.coverage.baseline_findings == len(existing)
    assert sarif["version"] == "2.1.0"
    assert sarif["runs"][0]["results"][0]["partialFingerprints"]


def test_report_1_reader_is_compatible_but_cannot_seed_reuse() -> None:
    legacy = Report.model_validate({"schema_version": "1.0", "scan_root": "legacy"})

    assert legacy.schema_version == "1.0"
    with pytest.raises(ValueError, match="Report 2.0"):
        create_baseline(legacy)
    with pytest.raises(ValueError, match="Report 2.0"):
        create_manifest(legacy, approve=set(), reject=set(), approve_all=False)


def test_strict_configuration_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        ScanConfig.model_validate({"unknown": True})


def test_malformed_project_yaml_has_actionable_error(tmp_path: Path) -> None:
    (tmp_path / ".uptocode.yml").write_text("rules: [", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid configuration"):
        load_config(tmp_path)


def test_single_file_scan_and_workspace_containment(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    inside = workspace / "inside.py"
    outside = tmp_path / "outside.py"
    inside.write_text("x = 1\n", encoding="utf-8")
    outside.write_text("x = 1\n", encoding="utf-8")

    assert scan_path(inside).coverage.files_analyzed == 1
    with pytest.raises(ValueError, match="outside"):
        audit_file(str(outside), workspace_root=workspace)
    link = workspace / "linked.py"
    try:
        link.symlink_to(outside)
    except OSError:
        pass
    else:
        with pytest.raises(ValueError, match="outside"):
            audit_file(str(link), workspace_root=workspace)


def test_static_scan_never_opens_a_network_connection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "agent.py"
    source.write_text("x = 1\n", encoding="utf-8")

    def deny_network(*args: object, **kwargs: object) -> None:
        raise AssertionError("static analysis attempted network access")

    monkeypatch.setattr(socket, "create_connection", deny_network)
    report = scan_path(source)

    assert report.coverage.files_analyzed == 1


def test_submitted_source_budget_fails_closed() -> None:
    with pytest.raises(ValueError, match="byte limit"):
        audit_source("#" * (MAX_SOURCE_BYTES + 1))
    with pytest.raises(ValueError, match="contained relative"):
        audit_source("x = 1\n", filename="../outside.py")


def test_cooperative_cancellation_preserves_partial_report(tmp_path: Path) -> None:
    (tmp_path / "agent.py").write_text("x = 1\n", encoding="utf-8")

    report = AuditService().scan(tmp_path, cancelled=lambda: True)

    assert report.coverage.files_analyzed == 0
    assert {warning.code for warning in report.analysis_warnings} == {"SCAN_CANCELLED"}


def test_submitted_source_is_not_persisted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import tempfile

    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    report = audit_source("x = 1\n")

    assert report.coverage.files_analyzed == 1
    assert list(tmp_path.iterdir()) == []


def test_submitted_report_output_budget_preserves_partial_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import uptocode.mcp_server as mcp_module

    monkeypatch.setattr(mcp_module, "MAX_REPORT_FINDINGS", 1)
    report = audit_source(
        "def first():\n    while True:\n        work()\n"
        "def second():\n    while True:\n        work()\n"
    )

    assert len(report.findings) == 1
    assert "REPORT_OUTPUT_BUDGET_EXCEEDED" in {
        warning.code for warning in report.analysis_warnings
    }


def test_hosted_server_never_registers_filesystem_tools() -> None:
    tools = asyncio.run(create_server(mode="hosted").list_tools())
    names = {tool.name for tool in tools}

    assert "audit_file" not in names
    assert "audit_repo" not in names
    assert "audit_source" in names
    assert all(tool.annotations and tool.annotations.readOnlyHint for tool in tools)
    assert all(tool.outputSchema.get("additionalProperties") is not True for tool in tools)


def test_hosted_auth_configuration_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UPTOCODE_API_KEY_HASHES", "not-a-digest")

    with pytest.raises(ValueError, match="SHA-256"):
        hosted_app()


def test_hosted_logs_are_payload_and_credential_free(caplog: pytest.LogCaptureFixture) -> None:
    token = "secret-email@example.com"
    sent: list[dict[str, object]] = []

    async def application(scope, receive, send) -> None:  # type: ignore[no-untyped-def]
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    async def receive() -> dict[str, object]:
        return {"type": "http.disconnect"}

    async def send(message: dict[str, object]) -> None:
        sent.append(message)

    middleware = BearerKeyMiddleware(
        application,
        {hashlib.sha256(token.encode()).hexdigest()},
        TokenBucketLimiter(),
    )
    caplog.set_level("INFO", logger="uptocode.mcp_server")
    asyncio.run(
        middleware(
            {
                "type": "http",
                "path": "/mcp",
                "headers": [(b"authorization", f"Bearer {token}".encode())],
            },
            receive,
            send,
        )
    )

    assert sent
    assert token not in caplog.text
    assert "example.com" not in caplog.text
    assert "correlation_id=" in caplog.text
    digest = hashlib.sha256(token.encode()).hexdigest()
    assert f"key_id={digest[:8]}" in caplog.text
    assert digest not in caplog.text


def test_local_diff_reads_only_contained_workspace_bases(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "agent.py").write_text("value = 1\n", encoding="utf-8")

    bases = _workspace_diff_bases("--- a/agent.py\n+++ b/agent.py\n", workspace)
    assert bases == {"agent.py": "value = 1\n"}
    with pytest.raises(ValueError, match="contained"):
        _workspace_diff_bases("--- ../outside.py\n+++ b/outside.py\n", workspace)


def test_cli_severity_override_and_github_output(tmp_path: Path) -> None:
    source = tmp_path / "loop.py"
    source.write_text("while True:\n    work()\n", encoding="utf-8")

    result = CliRunner().invoke(
        app,
        ["scan", str(source), "--format", "github", "--severity", "AA001=warning"],
    )

    assert result.exit_code == 0
    assert "::warning" in result.stdout
    assert "title=AA001" in result.stdout


def test_cli_eager_version_and_sarif_output(tmp_path: Path) -> None:
    source = tmp_path / "loop.py"
    source.write_text("while True:\n    work()\n", encoding="utf-8")

    version = CliRunner().invoke(app, ["--version"])
    sarif = CliRunner().invoke(app, ["scan", str(source), "--format", "sarif"])

    assert version.exit_code == 0
    assert version.stdout.strip() == "1.1.0"
    assert sarif.exit_code == 0
    assert json.loads(sarif.stdout)["version"] == "2.1.0"


def test_rule_layer_has_no_interface_or_network_dependencies() -> None:
    rules = Path(__file__).parents[1] / "uptocode" / "rules"
    forbidden = ("mcp.server", "typer", "openai", "starlette", "uvicorn")

    for module in rules.glob("*.py"):
        tree = ast.parse(module.read_text(encoding="utf-8"))
        imports = [
            node.module or ""
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        ] + [
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        ]
        assert not any(name.startswith(forbidden) for name in imports), module.name


def test_trusted_local_rulepack_protocol_is_versioned(tmp_path: Path) -> None:
    good = tmp_path / "good_pack.py"
    good.write_text(
        "from uptocode.rules.plugins import RulePluginResult\n"
        "class Pack:\n"
        "    api_version = '1.0'\n"
        "    def evaluate(self, context):\n"
        "        return RulePluginResult()\n"
        "plugin = Pack()\n",
        encoding="utf-8",
    )
    plugins = load_rule_plugins([str(good)], root=tmp_path)
    assert evaluate_plugins(plugins, RuleContext(files=[])).findings == []

    bad = tmp_path / "bad_pack.py"
    bad.write_text(
        "class Pack:\n"
        "    api_version = '2.0'\n"
        "    def evaluate(self, context):\n"
        "        return None\n"
        "plugin = Pack()\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unsupported API"):
        load_rule_plugins([str(bad)], root=tmp_path)
