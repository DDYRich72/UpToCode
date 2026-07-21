from __future__ import annotations

import ast
import asyncio
import shutil
import sys
from pathlib import Path
from typing import cast
from unittest.mock import Mock

from lsprotocol import types
from pygls.workspace import Workspace
import pytest
import pytest_lsp
from pytest_lsp import ClientServerConfig, LanguageClient
from pytest_lsp.client import client_capabilities

from uptocode.engine import AuditService, scan_path
from uptocode.lsp_server import (
    UpToCodeLanguageServer,
    _fixplan_has_fingerprint,
    code_actions,
    create_server,
    diagnostics_for_report,
)


STATIC_RULE_FIXTURES = [
    (rule_id, Path("fixtures/bad_python/agent.py"))
    for rule_id in (
        "AA001",
        "AA002",
        "AA003",
        "AA004",
        "AA006",
        "AA007",
        "AA010",
        "AA011",
        "AA012",
    )
] + [
    ("AA013", Path("fixtures/bad_python/z_context.py")),
] + [
    (rule_id, Path("fixtures/bad_mcp_server/server.py"))
    for rule_id in ("AA014", "AA015", "AA016", "AA017", "AA018")
]


@pytest_lsp.fixture(
    config=ClientServerConfig(server_command=[sys.executable, "-m", "uptocode", "lsp"]),
)
async def lsp_client(client: LanguageClient, tmp_path: Path):
    await client.initialize_session(
        types.InitializeParams(
            capabilities=client_capabilities("visual_studio_code"),
            root_uri=tmp_path.as_uri(),
            workspace_folders=[
                types.WorkspaceFolder(uri=tmp_path.as_uri(), name="fixture")
            ],
        )
    )
    yield
    await client.shutdown_session()


@pytest.mark.asyncio
async def test_lsp_open_diagnostics_match_static_cli(
    lsp_client: LanguageClient, tmp_path: Path
) -> None:
    source = Path("fixtures/bad_python/agent.py")
    target = tmp_path / "space in path" / "agent.py"
    target.parent.mkdir()
    shutil.copyfile(source, target)
    expected = scan_path(target)
    uri = target.as_uri()

    lsp_client.text_document_did_open(
        types.DidOpenTextDocumentParams(
            text_document=types.TextDocumentItem(
                uri=uri,
                language_id="python",
                version=1,
                text=target.read_text(encoding="utf-8"),
            )
        )
    )
    await lsp_client.wait_for_notification(types.TEXT_DOCUMENT_PUBLISH_DIAGNOSTICS)

    actual = lsp_client.diagnostics[uri]
    assert [(item.code, item.severity, item.range.start.line) for item in actual] == [
        (finding.rule_id, _lsp_severity(finding.severity.value), finding.line - 1)
        for finding in expected.findings
    ]
    assert [item.data["fingerprint"] for item in actual] == [
        finding.fingerprint for finding in expected.findings
    ]
    assert [item.data["maturity"] for item in actual] == [
        finding.maturity for finding in expected.findings
    ]
    assert [item.message for item in actual] == [
        f"{finding.title}"
        f"{' [experimental]' if finding.maturity == 'experimental' else ''}"
        f"{' — ' + finding.verdict.observed.strip() if finding.verdict.observed.strip() else ''}"
        for finding in expected.findings
    ]
    assert [item.code_description.href if item.code_description else None for item in actual] == [
        finding.citations[0].url if finding.citations else None
        for finding in expected.findings
    ]


@pytest.mark.asyncio
async def test_lsp_close_clears_diagnostics(
    lsp_client: LanguageClient, tmp_path: Path
) -> None:
    target = tmp_path / "agent.py"
    target.write_text("from openai import OpenAI\nclient = OpenAI()\n", encoding="utf-8")
    uri = target.as_uri()
    lsp_client.text_document_did_open(
        types.DidOpenTextDocumentParams(
            text_document=types.TextDocumentItem(
                uri=uri, language_id="python", version=1, text=target.read_text()
            )
        )
    )
    await lsp_client.wait_for_notification(types.TEXT_DOCUMENT_PUBLISH_DIAGNOSTICS)

    lsp_client.text_document_did_close(
        types.DidCloseTextDocumentParams(
            text_document=types.TextDocumentIdentifier(uri=uri)
        )
    )
    await lsp_client.wait_for_notification(types.TEXT_DOCUMENT_PUBLISH_DIAGNOSTICS)
    assert not lsp_client.diagnostics[uri]


@pytest.mark.asyncio
async def test_lsp_actions_and_suppression_round_trip(
    lsp_client: LanguageClient, tmp_path: Path
) -> None:
    target = tmp_path / "agent.py"
    shutil.copyfile(Path("fixtures/bad_python/agent.py"), target)
    report = scan_path(target)
    finding = report.findings[0]
    fixplan = tmp_path / "FIXPLAN.md"
    fixplan.write_text(f"# Plan\n\nFingerprint: `{finding.fingerprint}`\n", encoding="utf-8")
    uri = target.as_uri()
    lsp_client.text_document_did_open(
        types.DidOpenTextDocumentParams(
            text_document=types.TextDocumentItem(
                uri=uri,
                language_id="python",
                version=1,
                text=target.read_text(encoding="utf-8"),
            )
        )
    )
    await lsp_client.wait_for_notification(types.TEXT_DOCUMENT_PUBLISH_DIAGNOSTICS)
    diagnostic = next(
        item for item in lsp_client.diagnostics[uri] if item.data["fingerprint"] == finding.fingerprint
    )

    actions = await lsp_client.text_document_code_action_async(
        types.CodeActionParams(
            text_document=types.TextDocumentIdentifier(uri=uri),
            range=diagnostic.range,
            context=types.CodeActionContext(diagnostics=[diagnostic]),
        )
    )
    assert actions is not None
    # pytest-lsp 1.0.1 structures the Command | CodeAction response union as the
    # first member; inspect the nested wire payload it preserves in Command.command.
    wire_actions = [ast.literal_eval(item.command) for item in actions]
    assert [item["command"] for item in wire_actions] == [
        "uptocode.suppressWithMetadata",
        "uptocode.openCitation",
        "uptocode.openFixplan",
    ]
    assert wire_actions[0]["arguments"][0]["version"] == 1

    lines = target.read_text(encoding="utf-8").splitlines()
    lines.insert(
        finding.line - 1,
        f'# uptocode: ignore {finding.rule_id} owner=team reason="accepted" expires=2099-01-01',
    )
    updated = "\n".join(lines) + "\n"
    target.write_text(updated, encoding="utf-8")
    lsp_client.text_document_did_change(
        types.DidChangeTextDocumentParams(
            text_document=types.VersionedTextDocumentIdentifier(uri=uri, version=2),
            content_changes=[types.TextDocumentContentChangeWholeDocument(text=updated)],
        )
    )
    lsp_client.text_document_did_save(
        types.DidSaveTextDocumentParams(
            text_document=types.TextDocumentIdentifier(uri=uri)
        )
    )
    await lsp_client.wait_for_notification(types.TEXT_DOCUMENT_PUBLISH_DIAGNOSTICS)
    assert finding.fingerprint not in {
        item.data["fingerprint"] for item in lsp_client.diagnostics[uri]
    }
    suppressed = scan_path(target)
    assert any(
        item.rule == finding.rule_id and item.owner == "team"
        for item in suppressed.suppression_details
    )


def test_generation_gate_rejects_stale_results() -> None:
    server = UpToCodeLanguageServer()
    first = server.next_generation("file:///agent.py")
    second = server.next_generation("file:///agent.py")
    assert not server.current_generation("file:///agent.py", first)
    assert server.current_generation("file:///agent.py", second)


class _OrderedAudit:
    def __init__(self, reports: list[object]) -> None:
        self.reports = reports

    def scan(self, path: Path) -> object:
        report = self.reports.pop(0)
        if self.reports:
            import time

            time.sleep(0.05)
        return report


@pytest.mark.asyncio
async def test_rapid_analysis_discards_superseded_result(tmp_path: Path) -> None:
    target = tmp_path / "agent.py"
    target.write_text("pass\n", encoding="utf-8")
    old_report = scan_path(Path("fixtures/bad_python/agent.py"))
    clean_report = scan_path(target)
    server = UpToCodeLanguageServer(cast(AuditService, _OrderedAudit([old_report, clean_report])))
    workspace = Workspace(tmp_path.as_uri())
    workspace.put_text_document(
        types.TextDocumentItem(
            uri=target.as_uri(), language_id="python", version=2, text="pass\n"
        )
    )
    server.protocol._workspace = workspace  # type: ignore[attr-defined]
    publish = Mock()
    server.text_document_publish_diagnostics = publish

    first = asyncio.create_task(server.analyze(target.as_uri(), 1))
    await asyncio.sleep(0.01)
    second = asyncio.create_task(server.analyze(target.as_uri(), 2))
    await asyncio.gather(first, second)

    assert publish.call_count == 1
    assert publish.call_args.args[0].version == 2
    assert not publish.call_args.args[0].diagnostics


def _initialized_server(root: Path, target: Path) -> UpToCodeLanguageServer:
    server = create_server()
    workspace = Workspace(
        root.as_uri(),
        workspace_folders=[types.WorkspaceFolder(uri=root.as_uri(), name="root")],
    )
    workspace.put_text_document(
        types.TextDocumentItem(
            uri=target.as_uri(),
            language_id="python",
            version=3,
            text=target.read_text(encoding="utf-8"),
        )
    )
    server.protocol._workspace = workspace  # type: ignore[attr-defined]
    return server


def test_diagnostic_mapping_and_direct_code_actions(tmp_path: Path) -> None:
    target = tmp_path / "agent.py"
    shutil.copyfile(Path("fixtures/bad_python/agent.py"), target)
    report = scan_path(target)
    lines = target.read_text(encoding="utf-8").splitlines()
    diagnostics = diagnostics_for_report(report, lines=lines)
    finding = report.findings[0]
    diagnostic = diagnostics[0]
    assert diagnostic.code == finding.rule_id
    assert diagnostic.code_description is not None
    assert diagnostic.data["fingerprint"] == finding.fingerprint

    (tmp_path / "FIXPLAN.md").write_text(
        f"Fingerprint: `{finding.fingerprint}`\n", encoding="utf-8"
    )
    server = _initialized_server(tmp_path, target)
    params = types.CodeActionParams(
        text_document=types.TextDocumentIdentifier(uri=target.as_uri()),
        range=diagnostic.range,
        context=types.CodeActionContext(diagnostics=[diagnostic]),
    )
    actions = code_actions(server, params)
    assert [item.command.command if item.command else None for item in actions] == [
        "uptocode.suppressWithMetadata",
        "uptocode.openCitation",
        "uptocode.openFixplan",
    ]
    assert actions[0].command is not None
    assert actions[0].command.arguments[0]["version"] == 3
    assert actions[2].disabled is None

    foreign = types.Diagnostic(
        range=diagnostic.range,
        message="foreign",
        source="other",
    )
    params.context.diagnostics = [foreign]
    assert code_actions(server, params) == []


@pytest.mark.asyncio
async def test_direct_analysis_publishes_and_logs_without_source(tmp_path: Path) -> None:
    target = tmp_path / "broken.py"
    target.write_text("def broken(:\n", encoding="utf-8")
    server = _initialized_server(tmp_path, target)
    publish = Mock()
    log = Mock()
    server.text_document_publish_diagnostics = publish
    server.window_log_message = log

    await server.analyze(target.as_uri(), 3)
    assert not publish.call_args.args[0].diagnostics
    assert any(
        "PYTHON_PARSE_ERROR" in call.args[0].message for call in log.call_args_list
    )

    await server.analyze((tmp_path / "notes.txt").as_uri(), 1)
    await server.analyze("untitled:buffer", 1)
    assert publish.call_count == 1
    server.close_document(target.as_uri())
    assert publish.call_count == 2


class _FailingAudit:
    def scan(self, path: Path) -> None:
        raise ValueError("secret source must not enter the log")


@pytest.mark.asyncio
async def test_direct_analysis_failure_is_bounded(tmp_path: Path) -> None:
    target = tmp_path / "agent.py"
    target.write_text("pass\n", encoding="utf-8")
    server = UpToCodeLanguageServer(cast(AuditService, _FailingAudit()))
    workspace = Workspace(tmp_path.as_uri())
    workspace.put_text_document(
        types.TextDocumentItem(
            uri=target.as_uri(), language_id="python", version=1, text="pass\n"
        )
    )
    server.protocol._workspace = workspace  # type: ignore[attr-defined]
    publish = Mock()
    log = Mock()
    server.text_document_publish_diagnostics = publish
    server.window_log_message = log

    await server.analyze(target.as_uri(), 1)
    assert not publish.call_args.args[0].diagnostics
    assert log.call_args.args[0].message == "UpToCode scan failed: ValueError"


def test_fixplan_action_uses_deepest_workspace_and_disables_stale_entry(
    tmp_path: Path,
) -> None:
    workspace_root = tmp_path / "nested"
    workspace_root.mkdir()
    target = workspace_root / "agent.py"
    shutil.copyfile(Path("fixtures/bad_python/agent.py"), target)
    report = scan_path(target)
    diagnostic = diagnostics_for_report(
        report, lines=target.read_text(encoding="utf-8").splitlines()
    )[0]
    fingerprint = report.findings[0].fingerprint
    (tmp_path / "FIXPLAN.md").write_text(fingerprint, encoding="utf-8")
    server = create_server()
    workspace = Workspace(
        tmp_path.as_uri(),
        workspace_folders=[
            types.WorkspaceFolder(uri=tmp_path.as_uri(), name="outer"),
            types.WorkspaceFolder(uri=workspace_root.as_uri(), name="nested"),
        ],
    )
    workspace.put_text_document(
        types.TextDocumentItem(
            uri=target.as_uri(), language_id="python", version=1, text=target.read_text()
        )
    )
    server.protocol._workspace = workspace  # type: ignore[attr-defined]
    params = types.CodeActionParams(
        text_document=types.TextDocumentIdentifier(uri=target.as_uri()),
        range=diagnostic.range,
        context=types.CodeActionContext(diagnostics=[diagnostic]),
    )

    missing = code_actions(server, params)[2]
    assert missing.disabled is not None
    (workspace_root / "FIXPLAN.md").write_text("stale", encoding="utf-8")
    stale = code_actions(server, params)[2]
    assert stale.disabled is not None


def test_fixplan_fingerprint_match_is_exact() -> None:
    fingerprint = "e529db308cff0c2d511ad646"
    assert _fixplan_has_fingerprint(f"Fingerprint: `{fingerprint}`\n", fingerprint)
    assert not _fixplan_has_fingerprint(
        f"Fingerprint: `{fingerprint}0`\n", fingerprint
    )
    assert not _fixplan_has_fingerprint(f"note {fingerprint}\n", fingerprint)


def test_typescript_suppression_action_syntax_round_trip(tmp_path: Path) -> None:
    target = tmp_path / "agent.ts"
    shutil.copyfile(Path("fixtures/bad_ts/agent.ts"), target)
    finding = next(item for item in scan_path(target).findings if item.rule_id == "AA001")
    lines = target.read_text(encoding="utf-8").splitlines()
    lines.insert(
        finding.line - 1,
        '// uptocode: ignore AA001 owner=team reason="accepted" expires=2099-01-01',
    )
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report = scan_path(target)
    assert finding.fingerprint not in {item.fingerprint for item in report.findings}
    assert any(item.rule == "AA001" and item.owner == "team" for item in report.suppression_details)


def _lsp_severity(value: str) -> types.DiagnosticSeverity:
    return {
        "critical": types.DiagnosticSeverity.Error,
        "warning": types.DiagnosticSeverity.Warning,
        "info": types.DiagnosticSeverity.Information,
    }[value]


@pytest.mark.parametrize(("rule_id", "fixture"), STATIC_RULE_FIXTURES)
def test_each_static_rule_has_cli_equivalent_lsp_diagnostic(
    rule_id: str, fixture: Path
) -> None:
    report = scan_path(fixture)
    diagnostics = diagnostics_for_report(
        report, lines=fixture.read_text(encoding="utf-8").splitlines()
    )
    assert rule_id in {item.rule_id for item in report.findings}
    assert rule_id in {item.code for item in diagnostics}


def test_judgment_only_rules_remain_not_requested() -> None:
    report = scan_path(Path("fixtures/bad_python/agent.py"))
    statuses = {item.rule_id: item.status for item in report.rule_results}
    assert {rule_id: statuses[rule_id] for rule_id in ("AA005", "AA008", "AA009")} == {
        "AA005": "not_requested",
        "AA008": "not_requested",
        "AA009": "not_requested",
    }
