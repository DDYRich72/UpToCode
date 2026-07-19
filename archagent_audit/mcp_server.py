"""Typed, bounded local and hosted MCP interfaces over the shared AuditService."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import hashlib
import hmac
import json
import logging
import os
import secrets
import tempfile
import threading
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path
from typing import Annotated, Protocol, cast

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from archagent_audit import __version__
from archagent_audit.adapters.python import extract_python_evidence
from archagent_audit.diffing import reconstruct_unified_diff
from archagent_audit.engine import AuditService
from archagent_audit.models import (
    AnalysisWarning,
    Finding,
    RedactionCounts,
    Report,
    ReviewManifest,
    StrictModel,
)
from archagent_audit.planner import generate_fixplan as build_fixplan
from archagent_audit.redaction import redact_text
from archagent_audit.review import create_manifest
from archagent_audit.rules.aa001 import evaluate_aa001
from archagent_audit.rules.registry import load_core_rules
from archagent_audit.schema_validation import ToolSchemaResult, validate_tool_schema


MAX_SOURCE_BYTES = 1024 * 1024
MAX_REQUEST_SOURCE_BYTES = 4 * 1024 * 1024
MAX_REPORT_FINDINGS = 1_000
MAX_SOURCE_FILES = 256
READ_ONLY = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)
logger = logging.getLogger(__name__)

ASGIMessage = dict[str, object]
ASGIScope = dict[str, object]
ASGIReceive = Callable[[], Awaitable[ASGIMessage]]
ASGISend = Callable[[ASGIMessage], Awaitable[None]]


class ASGIApplication(Protocol):
    async def __call__(
        self,
        scope: ASGIScope,
        receive: ASGIReceive,
        send: ASGISend,
    ) -> None: ...


SourceInput = Annotated[
    str,
    Field(
        min_length=1,
        max_length=MAX_SOURCE_BYTES,
        description="One explicitly submitted UTF-8 Python source document (maximum 1 MiB).",
        examples=["from agents import Agent\nagent = Agent(name='bounded')\n"],
    ),
]
FilenameInput = Annotated[
    str,
    Field(
        min_length=1,
        max_length=512,
        description="Contained relative Python filename used only for report locations.",
        examples=["src/agent.py"],
    ),
]
PathInput = Annotated[
    str,
    Field(
        min_length=1,
        max_length=4_096,
        description="Local path that must resolve inside the configured workspace root.",
        examples=["/workspace/src/agent.py"],
    ),
]
DiffInput = Annotated[
    str,
    Field(
        min_length=1,
        max_length=MAX_REQUEST_SOURCE_BYTES,
        description="Unified diff with file headers, hunks, and context (maximum 4 MiB).",
        examples=["--- /dev/null\n+++ b/agent.py\n@@ -0,0 +1 @@\n+x = 1\n"],
    ),
]
JsonInput = Annotated[
    str,
    Field(
        min_length=2,
        max_length=MAX_REQUEST_SOURCE_BYTES,
        description="Strict JSON document for the named ArchAgent contract.",
        examples=["{}"],
    ),
]
RuleIdInput = Annotated[
    str,
    Field(
        pattern=r"^AA\d{3}$",
        description="ArchAgent rule identifier in AA001 through AA012 form.",
        examples=["AA001"],
    ),
]
JudgmentFlag = Annotated[
    bool,
    Field(description="Enable optional bounded model judgment; false keeps analysis offline."),
]
SendCodeFlag = Annotated[
    bool,
    Field(description="Explicit consent to send redacted excerpts when judgment is enabled."),
]
BaseFilesInput = Annotated[
    dict[str, str] | None,
    Field(
        max_length=MAX_SOURCE_FILES,
        description="Explicit old-path to UTF-8 base content mapping for modified files.",
    ),
]
DecisionId = Annotated[
    str,
    Field(min_length=1, max_length=128, description="Finding fingerprint or rule identifier."),
]
DecisionList = Annotated[
    list[DecisionId] | None,
    Field(
        max_length=MAX_REPORT_FINDINGS,
        description="Finding fingerprints or rule identifiers to decide.",
    ),
]
ApprovalFlag = Annotated[
    bool,
    Field(description="Approve every finding in the exact supplied Report 2.0 document."),
]


class LoopCheckResult(StrictModel):
    findings: list[Finding] = Field(default_factory=list)
    analysis_warnings: list[AnalysisWarning] = Field(default_factory=list)
    redactions: RedactionCounts = Field(default_factory=RedactionCounts)


class RuleInfo(StrictModel):
    id: str
    name: str
    tier: str
    severity: str
    citations: list[str]


class RuleCatalog(StrictModel):
    rules: list[RuleInfo]


class RuleLookupResult(StrictModel):
    rule: RuleInfo | None = None
    error_code: str | None = None
    message: str | None = None


class MarkdownResult(StrictModel):
    markdown: str


def _bounded_text(value: str, *, name: str, maximum: int = MAX_SOURCE_BYTES) -> None:
    size = len(value.encode("utf-8"))
    if size > maximum:
        raise ValueError(f"{name} exceeds the {maximum}-byte limit")


def _contained_path(path: str | Path, root: Path | None) -> Path:
    resolved = Path(path).resolve(strict=True)
    if root is not None:
        allowed = root.resolve(strict=True)
        try:
            resolved.relative_to(allowed)
        except ValueError as error:
            raise ValueError("Path is outside the configured workspace root") from error
    return resolved


def _scan_sources(
    sources: dict[str, str],
    *,
    judgment: bool = False,
    send_code: bool = False,
) -> Report:
    if judgment and not send_code:
        raise ValueError("judgment=true requires send_code=true")
    if len(sources) > MAX_SOURCE_FILES:
        raise ValueError(f"Submitted source exceeds the {MAX_SOURCE_FILES}-file limit")
    aggregate = sum(
        len(name.encode("utf-8")) + len(value.encode("utf-8"))
        for name, value in sources.items()
    )
    if aggregate > MAX_REQUEST_SOURCE_BYTES:
        raise ValueError(f"Submitted source exceeds the {MAX_REQUEST_SOURCE_BYTES}-byte request limit")
    with tempfile.TemporaryDirectory(prefix="archagent-audit-") as directory:
        root = Path(directory)
        for filename, source in sources.items():
            _bounded_text(filename, name="filename", maximum=512)
            _bounded_text(source, name=filename)
            relative = Path(filename)
            if relative.is_absolute() or ".." in relative.parts or relative.suffix.lower() != ".py":
                raise ValueError("Submitted filenames must be contained relative Python paths")
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(source, encoding="utf-8")
        report = AuditService().scan(root, judgment=judgment, send_code=send_code)
    if len(report.findings) > MAX_REPORT_FINDINGS:
        omitted = len(report.findings) - MAX_REPORT_FINDINGS
        report.findings = report.findings[:MAX_REPORT_FINDINGS]
        report.analysis_warnings.append(
            AnalysisWarning(
                code="REPORT_OUTPUT_BUDGET_EXCEEDED",
                message=f"The report omitted {omitted} findings after reaching its output budget.",
            )
        )
    if report.coverage.files_analyzed == 0:
        raise ValueError("Submitted Python source could not be analyzed")
    report.scan_root = "<submitted-code>"
    return report


def audit_source(
    source: SourceInput,
    filename: FilenameInput = "snippet.py",
    judgment: JudgmentFlag = False,
    send_code: SendCodeFlag = False,
) -> Report:
    """Audit one explicitly submitted Python source document."""
    return _scan_sources(
        {filename: source}, judgment=judgment, send_code=send_code
    )


def audit_file(
    path: PathInput,
    judgment: JudgmentFlag = False,
    send_code: SendCodeFlag = False,
    *,
    workspace_root: Path | None = None,
) -> Report:
    """Audit one local Python file contained by the configured workspace root."""
    source_path = _contained_path(path, workspace_root)
    if not source_path.is_file() or source_path.suffix.lower() != ".py":
        raise ValueError(f"Python file not found: {source_path}")
    try:
        source = source_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(f"Python file is not UTF-8: {source_path}") from error
    return audit_source(
        source,
        filename=source_path.name,
        judgment=judgment,
        send_code=send_code,
    )


def audit_repo(
    path: PathInput,
    judgment: JudgmentFlag = False,
    send_code: SendCodeFlag = False,
    *,
    workspace_root: Path | None = None,
) -> Report:
    """Audit a local repository contained by the configured workspace root."""
    repository = _contained_path(path, workspace_root)
    if not repository.is_dir():
        raise ValueError(f"Repository directory not found: {repository}")
    return AuditService().scan(repository, judgment=judgment, send_code=send_code)


def audit_diff(
    diff: DiffInput,
    base_files: BaseFilesInput = None,
    judgment: JudgmentFlag = False,
    send_code: SendCodeFlag = False,
) -> Report:
    """Reconstruct and audit changed Python files from a unified diff."""
    _bounded_text(diff, name="diff", maximum=MAX_REQUEST_SOURCE_BYTES)
    base_files = base_files or {}
    if len(base_files) > MAX_SOURCE_FILES:
        raise ValueError(f"Diff base content exceeds the {MAX_SOURCE_FILES}-file limit")
    request_size = len(diff.encode("utf-8")) + sum(
        len(name.encode("utf-8")) + len(value.encode("utf-8"))
        for name, value in base_files.items()
    )
    if request_size > MAX_REQUEST_SOURCE_BYTES:
        raise ValueError(f"Diff request exceeds the {MAX_REQUEST_SOURCE_BYTES}-byte limit")
    for name, value in base_files.items():
        _bounded_text(value, name=name)
    patched = reconstruct_unified_diff(diff, base_files=base_files)
    sources = {
        item.new_path: item.source
        for item in patched
        if item.new_path is not None and item.new_path.lower().endswith(".py") and not item.deleted
    }
    if not sources:
        raise ValueError("Diff contains no analyzable Python files")
    return _scan_sources(sources, judgment=judgment, send_code=send_code)


def _workspace_diff_bases(diff: str, workspace_root: Path) -> dict[str, str]:
    bases: dict[str, str] = {}
    for line in diff.splitlines():
        if not line.startswith("--- "):
            continue
        value = line[4:].split("\t", 1)[0].strip()
        if value == "/dev/null":
            continue
        relative = value[2:] if value.startswith("a/") else value
        candidate = Path(relative)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise ValueError("Diff paths must be relative and contained")
        resolved = _contained_path(workspace_root / candidate, workspace_root)
        if not resolved.is_file():
            raise ValueError(f"Diff base file not found: {relative}")
        source = resolved.read_text(encoding="utf-8")
        _bounded_text(source, name=relative)
        bases[relative.replace("\\", "/")] = source
    return bases


def check_tool_schema(
    schema_json: JsonInput,
    judgment: JudgmentFlag = False,
    send_code: SendCodeFlag = False,
) -> ToolSchemaResult:
    """Validate a strict function-tool descriptor and JSON Schema 2020-12 input."""
    if judgment and not send_code:
        raise ValueError("judgment=true requires send_code=true")
    _bounded_text(schema_json, name="schema_json")
    try:
        schema = json.loads(schema_json)
    except json.JSONDecodeError as error:
        return ToolSchemaResult.model_validate(
            {"valid": False, "issues": [{"field": "$", "message": str(error)}]}
        )
    result = validate_tool_schema(schema)
    if judgment:
        result.judgment_status = "not-applicable"
    return result


def check_loop(snippet: SourceInput) -> LoopCheckResult:
    """Check a bounded Python loop or Runner invocation for AA001."""
    _bounded_text(snippet, name="snippet")
    redacted, counts = redact_text(snippet)
    try:
        evidence = extract_python_evidence(redacted)
    except SyntaxError as error:
        return LoopCheckResult(
            analysis_warnings=[
                AnalysisWarning(
                    code="PYTHON_PARSE_ERROR",
                    message="Python snippet could not be parsed.",
                    line=error.lineno,
                )
            ],
            redactions=counts,
        )
    lines = redacted.splitlines()
    findings: list[Finding] = []
    warnings: list[AnalysisWarning] = []
    for loop in evidence.loops:
        excerpt = "\n".join(lines[max(0, loop.line - 2): min(len(lines), loop.line + 1)])
        finding, warning = evaluate_aa001(loop, file="snippet.py", excerpt=excerpt)
        if finding:
            findings.append(finding)
        if warning:
            warnings.append(warning)
    return LoopCheckResult(findings=findings, analysis_warnings=warnings, redactions=counts)


def list_rules() -> RuleCatalog:
    """Return the complete trusted ArchAgent rule catalog."""
    return RuleCatalog(
        rules=[
            RuleInfo(
                id=item.id,
                name=item.name,
                tier=item.tier,
                severity=item.severity.value,
                citations=[str(url).rstrip("/") for url in item.citations],
            )
            for item in load_core_rules()
        ]
    )


def get_rule(rule_id: RuleIdInput) -> RuleLookupResult:
    """Return trusted metadata for one rule identifier."""
    normalized = rule_id.upper()
    for item in list_rules().rules:
        if item.id == normalized:
            return RuleLookupResult(rule=item)
    return RuleLookupResult(
        error_code="RULE_NOT_FOUND",
        message=f"Unknown ArchAgent rule: {normalized}",
    )


def review_findings(
    report_json: JsonInput,
    approve: DecisionList = None,
    reject: DecisionList = None,
    approve_all: ApprovalFlag = False,
) -> ReviewManifest:
    """Create an immutable review manifest from explicit finding decisions."""
    report = Report.model_validate_json(report_json)
    return create_manifest(
        report,
        approve=set(approve or []),
        reject=set(reject or []),
        approve_all=approve_all,
    )


def generate_fixplan(report_json: JsonInput, manifest_json: JsonInput) -> MarkdownResult:
    """Generate a non-mutating remediation plan from approved findings."""
    report = Report.model_validate_json(report_json)
    manifest = ReviewManifest.model_validate_json(manifest_json)
    return MarkdownResult(markdown=build_fixplan(report, manifest))


def create_server(*, mode: str = "local", workspace_root: Path | None = None) -> FastMCP:
    if mode not in {"local", "hosted"}:
        raise ValueError("MCP mode must be local or hosted")
    mcp = FastMCP(
        f"ArchAgent {__version__}",
        instructions=(
            "Bounded architecture-quality analysis for Python agent code. Static analysis "
            "is offline; judgment requires judgment=true and send_code=true."
        ),
        json_response=True,
        stateless_http=mode == "hosted",
    )
    mcp.add_tool(audit_source, annotations=READ_ONLY)
    if mode == "hosted":
        mcp.add_tool(audit_diff, annotations=READ_ONLY)
    mcp.add_tool(check_tool_schema, annotations=READ_ONLY)
    mcp.add_tool(check_loop, annotations=READ_ONLY)
    mcp.add_tool(list_rules, annotations=READ_ONLY)
    mcp.add_tool(get_rule, annotations=READ_ONLY)
    mcp.add_tool(review_findings, annotations=READ_ONLY)
    mcp.add_tool(generate_fixplan, annotations=READ_ONLY)

    @mcp.resource("archagent://rules")
    def rules_resource() -> str:
        """Return the trusted rule catalog as JSON."""
        return list_rules().model_dump_json(indent=2)

    if mode == "local":
        def audit_diff_local(
            diff: DiffInput,
            judgment: JudgmentFlag = False,
            send_code: SendCodeFlag = False,
        ) -> Report:
            root = (workspace_root or Path.cwd()).resolve(strict=True)
            logger.info("Local diff audit started")
            bases = _workspace_diff_bases(diff, root)
            logger.info("Local diff bases resolved: %d", len(bases))
            result = audit_diff(
                diff,
                bases,
                judgment,
                send_code,
            )
            logger.info("Local diff audit completed")
            return result

        async def audit_file_local(
            path: PathInput,
            ctx: Context,
            judgment: JudgmentFlag = False,
            send_code: SendCodeFlag = False,
        ) -> Report:
            await ctx.report_progress(0, 1, "Reading bounded source")
            result = await asyncio.to_thread(
                audit_file,
                path,
                judgment,
                send_code,
                workspace_root=workspace_root,
            )
            await ctx.report_progress(1, 1, "Audit complete")
            return result

        async def audit_repo_local(
            path: PathInput,
            ctx: Context,
            judgment: JudgmentFlag = False,
            send_code: SendCodeFlag = False,
        ) -> Report:
            await ctx.report_progress(0, 1, "Scanning bounded workspace")
            repository = _contained_path(path, workspace_root)
            if not repository.is_dir():
                raise ValueError(f"Repository directory not found: {repository}")
            cancelled = threading.Event()
            task = asyncio.create_task(
                asyncio.to_thread(
                    AuditService().scan,
                    repository,
                    judgment=judgment,
                    send_code=send_code,
                    cancelled=cancelled.is_set,
                )
            )
            try:
                result = await task
            except asyncio.CancelledError:
                cancelled.set()
                raise
            await ctx.report_progress(1, 1, "Audit complete")
            return result

        mcp.add_tool(audit_diff_local, name="audit_diff", annotations=READ_ONLY)
        mcp.add_tool(audit_file_local, name="audit_file", annotations=READ_ONLY)
        mcp.add_tool(audit_repo_local, name="audit_repo", annotations=READ_ONLY)
    _harden_tool_contracts(mcp)
    return mcp


def _harden_tool_contracts(mcp: FastMCP) -> None:
    """Make SDK-generated argument models reject and advertise unknown fields."""
    for tool in mcp._tool_manager._tools.values():
        argument_model = tool.fn_metadata.arg_model
        argument_model.model_config["extra"] = "forbid"
        argument_model.model_rebuild(force=True)
        tool.parameters = argument_model.model_json_schema()


server = create_server()


class BearerKeyMiddleware:
    """Small payload-blind ASGI authorization boundary for private beta access."""

    def __init__(self, app: ASGIApplication, hashes: set[str]) -> None:
        self.app = app
        self.hashes = hashes

    async def __call__(
        self,
        scope: ASGIScope,
        receive: ASGIReceive,
        send: ASGISend,
    ) -> None:
        started = time.monotonic()
        raw_headers = cast(list[tuple[bytes, bytes]], scope.get("headers", []))
        headers = {key.lower(): value for key, value in raw_headers}
        correlation_id = secrets.token_hex(16)
        state = cast(dict[str, object], scope.setdefault("state", {}))
        state["correlation_id"] = correlation_id
        status = 500

        async def send_with_correlation(message: ASGIMessage) -> None:
            nonlocal status
            if message.get("type") == "http.response.start":
                status = int(cast(int, message.get("status", 500)))
                response_headers = list(
                    cast(list[tuple[bytes, bytes]], message.get("headers", []))
                )
                response_headers.append((b"x-request-id", correlation_id.encode("ascii")))
                message = {**message, "headers": response_headers}
            await send(message)

        if scope.get("type") == "http" and scope.get("path") not in {"/healthz", "/readyz"}:
            value = headers.get(b"authorization", b"").decode("ascii", errors="ignore")
            token = value[7:] if value[:7].lower() == "bearer " else ""
            digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
            matches = [hmac.compare_digest(digest, item) for item in self.hashes]
            if not token or not any(matches):
                await send_with_correlation(
                    {
                        "type": "http.response.start",
                        "status": 401,
                        "headers": [(b"content-type", b"application/json")],
                    }
                )
                await send_with_correlation(
                    {"type": "http.response.body", "body": b'{"error":"unauthorized"}'}
                )
                logger.info(
                    "Hosted request completed correlation_id=%s status=%d duration_ms=%d",
                    correlation_id,
                    status,
                    round((time.monotonic() - started) * 1000),
                )
                return
        await self.app(scope, receive, send_with_correlation)
        logger.info(
            "Hosted request completed correlation_id=%s status=%d duration_ms=%d",
            correlation_id,
            status,
            round((time.monotonic() - started) * 1000),
        )


def hosted_app() -> ASGIApplication:
    """Build the stateless hosted ASGI app without path-bearing tools."""
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Mount, Route

    hashes = {item.strip().lower() for item in os.getenv("ARCHAGENT_API_KEY_HASHES", "").split(",") if item.strip()}
    if not hashes:
        raise ValueError("ARCHAGENT_API_KEY_HASHES must contain at least one SHA-256 key hash")
    invalid_hash = any(
        len(item) != 64
        or any(character not in "0123456789abcdef" for character in item)
        for item in hashes
    )
    if invalid_hash:
        raise ValueError("ARCHAGENT_API_KEY_HASHES must contain only hexadecimal SHA-256 digests")
    hosted = create_server(mode="hosted")

    async def health(_: object) -> JSONResponse:
        return JSONResponse({"status": "ok", "version": __version__})

    @asynccontextmanager
    async def lifespan(_: object) -> AsyncIterator[None]:
        async with hosted.session_manager.run():
            yield

    app = Starlette(
        routes=[
            Route("/healthz", health),
            Route("/readyz", health),
            Mount("/", app=hosted.streamable_http_app()),
        ],
        lifespan=lifespan,
    )
    return BearerKeyMiddleware(cast(ASGIApplication, app), hashes)


def run_server(
    *,
    transport: str = "stdio",
    root: Path | None = None,
    mode: str = "local",
) -> None:
    """Run bounded local stdio or hosted Streamable HTTP transport."""
    if transport == "stdio":
        create_server(mode="local", workspace_root=(root or Path.cwd())).run(transport="stdio")
        return
    if transport != "streamable-http" or mode != "hosted":
        raise ValueError("Hosted mode requires --transport streamable-http --mode hosted")
    import uvicorn

    uvicorn.run(hosted_app(), host="0.0.0.0", port=int(os.getenv("PORT", "8080")), log_level="info")


if __name__ == "__main__":
    run_server()
