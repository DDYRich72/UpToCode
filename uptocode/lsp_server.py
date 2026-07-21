"""Persistent file-scoped Language Server Protocol integration."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from lsprotocol import types
from pygls.lsp.server import LanguageServer
from pygls.uris import to_fs_path

from uptocode.config import SUPPORTED_SOURCE_EXTENSIONS
from uptocode.engine import AuditService
from uptocode.models import Finding, Report, Severity
from uptocode import __version__


_SEVERITIES = {
    Severity.CRITICAL: types.DiagnosticSeverity.Error,
    Severity.WARNING: types.DiagnosticSeverity.Warning,
    Severity.INFO: types.DiagnosticSeverity.Information,
}


def _message(finding: Finding) -> str:
    experimental = " [experimental]" if finding.maturity == "experimental" else ""
    observed = finding.verdict.observed.strip()
    return f"{finding.title}{experimental}{f' — {observed}' if observed else ''}"


def diagnostics_for_report(report: Report, *, lines: list[str]) -> list[types.Diagnostic]:
    """Map strict report findings into deterministic full-line LSP diagnostics."""
    diagnostics: list[types.Diagnostic] = []
    for finding in report.findings:
        line = max(0, finding.line - 1)
        length = len(lines[line]) if line < len(lines) else 0
        citation = finding.citations[0].url if finding.citations else None
        diagnostics.append(
            types.Diagnostic(
                range=types.Range(
                    start=types.Position(line=line, character=0),
                    end=types.Position(line=line, character=length),
                ),
                message=_message(finding),
                severity=_SEVERITIES[finding.severity],
                code=finding.rule_id,
                code_description=(
                    types.CodeDescription(href=citation) if citation is not None else None
                ),
                source="uptocode",
                data={
                    "fingerprint": finding.fingerprint,
                    "ruleId": finding.rule_id,
                    "maturity": finding.maturity,
                    "file": finding.file,
                    "line": finding.line,
                    "citation": citation,
                },
            )
        )
    return diagnostics


class UpToCodeLanguageServer(LanguageServer):  # type: ignore[misc]
    """Stateful pygls server with per-document stale-result protection."""

    def __init__(self, audit: AuditService | None = None) -> None:
        super().__init__(
            "uptocode-lsp",
            __version__,
            text_document_sync_kind=types.TextDocumentSyncKind.Incremental,
        )
        self.audit = audit or AuditService()
        self._generations: dict[str, int] = {}

    def next_generation(self, uri: str) -> int:
        generation = self._generations.get(uri, 0) + 1
        self._generations[uri] = generation
        return generation

    def current_generation(self, uri: str, generation: int) -> bool:
        return self._generations.get(uri) == generation

    async def analyze(self, uri: str, version: int | None) -> None:
        path_value = to_fs_path(uri)
        if path_value is None:
            return
        path = Path(path_value)
        if path.suffix.lower() not in SUPPORTED_SOURCE_EXTENSIONS:
            return
        generation = self.next_generation(uri)
        try:
            report = await asyncio.to_thread(self.audit.scan, path)
            document = self.workspace.get_text_document(uri)
            diagnostics = diagnostics_for_report(report, lines=document.lines)
        except (OSError, ValueError, UnicodeDecodeError, SyntaxError) as error:
            if not self.current_generation(uri, generation):
                return
            self.window_log_message(
                types.LogMessageParams(
                    type=types.MessageType.Error,
                    message=f"UpToCode scan failed: {type(error).__name__}",
                )
            )
            diagnostics = []
            report = None
        if not self.current_generation(uri, generation):
            return
        self.text_document_publish_diagnostics(
            types.PublishDiagnosticsParams(
                uri=uri,
                diagnostics=diagnostics,
                version=version,
            )
        )
        if report is not None:
            for warning in report.analysis_warnings:
                self.window_log_message(
                    types.LogMessageParams(
                        type=types.MessageType.Warning,
                        message=f"{warning.code}: {warning.message}",
                    )
                )

    def close_document(self, uri: str) -> None:
        self.next_generation(uri)
        self.text_document_publish_diagnostics(
            types.PublishDiagnosticsParams(uri=uri, diagnostics=[])
        )


def _diagnostic_data(diagnostic: types.Diagnostic) -> dict[str, Any] | None:
    if diagnostic.source != "uptocode" or not isinstance(diagnostic.data, dict):
        return None
    fingerprint = diagnostic.data.get("fingerprint")
    rule_id = diagnostic.data.get("ruleId")
    if not isinstance(fingerprint, str) or not isinstance(rule_id, str):
        return None
    return diagnostic.data


def _workspace_root(server: UpToCodeLanguageServer, uri: str) -> Path | None:
    path_value = to_fs_path(uri)
    if path_value is None:
        return None
    path = Path(path_value).resolve()
    candidates: list[Path] = []
    for folder in server.workspace.folders.values():
        folder_path = to_fs_path(folder.uri)
        if folder_path is None:
            continue
        root = Path(folder_path).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            continue
        candidates.append(root)
    return max(candidates, key=lambda item: len(item.parts), default=None)


def _fixplan_has_fingerprint(content: str, fingerprint: str) -> bool:
    return f"Fingerprint: `{fingerprint}`" in content.splitlines()


def code_actions(
    server: UpToCodeLanguageServer, params: types.CodeActionParams
) -> list[types.CodeAction]:
    """Return explicit client-executed actions for UpToCode diagnostics."""
    actions: list[types.CodeAction] = []
    for diagnostic in params.context.diagnostics:
        data = _diagnostic_data(diagnostic)
        if data is None:
            continue
        payload = {
            "uri": params.text_document.uri,
            "version": server.workspace.get_text_document(params.text_document.uri).version,
            "line": diagnostic.range.start.line,
            "ruleId": data["ruleId"],
            "fingerprint": data["fingerprint"],
        }
        actions.append(
            types.CodeAction(
                title=f"Suppress {data['ruleId']} with metadata…",
                kind=types.CodeActionKind.QuickFix,
                diagnostics=[diagnostic],
                command=types.Command(
                    title="Suppress with metadata",
                    command="uptocode.suppressWithMetadata",
                    arguments=[payload],
                ),
            )
        )
        citation = data.get("citation")
        if isinstance(citation, str):
            actions.append(
                types.CodeAction(
                    title=f"Open {data['ruleId']} citation",
                    diagnostics=[diagnostic],
                    command=types.Command(
                        title="Open citation",
                        command="uptocode.openCitation",
                        arguments=[citation],
                    ),
                )
            )
        root = _workspace_root(server, params.text_document.uri)
        fixplan = root / "FIXPLAN.md" if root is not None else None
        has_entry = False
        if fixplan is not None and fixplan.is_file():
            try:
                has_entry = _fixplan_has_fingerprint(
                    fixplan.read_text(encoding="utf-8"), data["fingerprint"]
                )
            except (OSError, UnicodeDecodeError):
                has_entry = False
        actions.append(
            types.CodeAction(
                title=f"Open {data['ruleId']} FIXPLAN entry",
                diagnostics=[diagnostic],
                disabled=(
                    None
                    if has_entry
                    else types.CodeActionDisabled(
                        reason="No matching fingerprint in workspace FIXPLAN.md"
                    )
                ),
                command=(
                    types.Command(
                        title="Open FIXPLAN entry",
                        command="uptocode.openFixplan",
                        arguments=[
                            {
                                "uri": fixplan.as_uri(),
                                "fingerprint": data["fingerprint"],
                            }
                        ],
                    )
                    if has_entry and fixplan is not None
                    else None
                ),
            )
        )
    return actions


def create_server(audit: AuditService | None = None) -> UpToCodeLanguageServer:
    server = UpToCodeLanguageServer(audit)

    @server.feature(types.TEXT_DOCUMENT_DID_OPEN)
    async def did_open(
        ls: UpToCodeLanguageServer, params: types.DidOpenTextDocumentParams
    ) -> None:
        await ls.analyze(params.text_document.uri, params.text_document.version)

    @server.feature(types.TEXT_DOCUMENT_DID_SAVE)
    async def did_save(
        ls: UpToCodeLanguageServer, params: types.DidSaveTextDocumentParams
    ) -> None:
        document = ls.workspace.get_text_document(params.text_document.uri)
        await ls.analyze(params.text_document.uri, document.version)

    @server.feature(types.TEXT_DOCUMENT_DID_CLOSE)
    def did_close(
        ls: UpToCodeLanguageServer, params: types.DidCloseTextDocumentParams
    ) -> None:
        ls.close_document(params.text_document.uri)

    @server.feature(types.TEXT_DOCUMENT_CODE_ACTION)
    def handle_code_action(
        ls: UpToCodeLanguageServer, params: types.CodeActionParams
    ) -> list[types.CodeAction]:
        return code_actions(ls, params)

    return server


def run_stdio() -> None:
    """Run the production stdio language server."""
    create_server().start_io()
