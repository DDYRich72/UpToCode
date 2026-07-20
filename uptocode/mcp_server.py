"""Typed, bounded local and hosted MCP interfaces over the shared AuditService."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import hashlib
import hmac
from importlib.metadata import PackageNotFoundError, version as package_version
import json
import logging
import math
import os
import secrets
import tempfile
import threading
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path
from typing import Annotated, Any, Protocol, cast

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from pydantic import Field

from uptocode import __version__
from uptocode.adapters.python import extract_python_evidence
from uptocode.diffing import reconstruct_unified_diff
from uptocode.engine import AuditService
from uptocode.models import (
    AnalysisWarning,
    Citation,
    Finding,
    RedactionCounts,
    Report,
    ReviewManifest,
    StrictModel,
)
from uptocode.planner import generate_fixplan as build_fixplan
from uptocode.redaction import redact_text
from uptocode.review import create_manifest
from uptocode.rules.aa001 import evaluate_aa001
from uptocode.rules.registry import load_core_rules
from uptocode.schema_validation import ToolSchemaResult, validate_tool_schema


MAX_SOURCE_BYTES = 1024 * 1024
MAX_REQUEST_SOURCE_BYTES = 4 * 1024 * 1024
MAX_REPORT_FINDINGS = 1_000
MAX_SOURCE_FILES = 256
MCP_FASTMCP_COMPAT_VERSION = "1.28.1"
DEFAULT_RATE_LIMIT_PER_MINUTE = 30
MAX_RATE_LIMIT_BUCKETS = 1_024
RATE_LIMIT_IDLE_SECONDS = 600.0
KEY_ID_PREFIX_LENGTH = 8
READ_ONLY = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)
logger = logging.getLogger(__name__)

try:
    MCP_SDK_VERSION = package_version("mcp")
except PackageNotFoundError:  # pragma: no cover - package dependency is required at runtime
    MCP_SDK_VERSION = "not-installed"

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
        description="Strict JSON document for the named UpToCode contract.",
        examples=["{}"],
    ),
]
RuleIdInput = Annotated[
    str,
    Field(
        pattern=r"^AA\d{3}$",
        description=(
            "UpToCode rule identifier; registered values are "
            + ", ".join(item.id for item in load_core_rules())
            + "."
        ),
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
    Field(description="Approve every finding in the exact supplied Report 2.x document."),
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
    maturity: str
    citations: list[Citation]


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
    candidate = Path(path)
    if root is not None:
        allowed = root.resolve(strict=True)
        if not candidate.is_absolute():
            candidate = allowed / candidate
    resolved = candidate.resolve(strict=True)
    if root is not None:
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
    with tempfile.TemporaryDirectory(prefix="uptocode-") as directory:
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
) -> ToolSchemaResult:
    """Validate a strict function-tool descriptor and JSON Schema 2020-12 input."""
    _bounded_text(schema_json, name="schema_json")
    try:
        schema = json.loads(schema_json)
    except json.JSONDecodeError as error:
        return ToolSchemaResult.model_validate(
            {"valid": False, "issues": [{"field": "$", "message": str(error)}]}
        )
    return validate_tool_schema(schema)


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
    """Return the complete trusted UpToCode rule catalog."""
    return RuleCatalog(
        rules=[
            RuleInfo(
                id=item.id,
                name=item.name,
                tier=item.tier,
                severity=item.severity.value,
                maturity=item.maturity,
                citations=[citation.to_public() for citation in item.citations],
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
        message=f"Unknown UpToCode rule: {normalized}",
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


def _hosted_judgment_guard(*, judgment: bool, enabled: bool) -> None:
    if judgment and not enabled:
        raise ValueError(
            "Hosted judgment is disabled; set UPTOCODE_HOSTED_JUDGMENT=true explicitly"
        )


def create_server(
    *,
    mode: str = "local",
    workspace_root: Path | None = None,
    hosted_judgment_enabled: bool = False,
    transport_security: TransportSecuritySettings | None = None,
) -> FastMCP:
    if mode not in {"local", "hosted"}:
        raise ValueError("MCP mode must be local or hosted")
    effective_root: Path | None = None
    if mode == "local":
        effective_root = (workspace_root or Path.cwd()).resolve(strict=True)
        if not effective_root.is_dir():
            raise ValueError(f"MCP workspace root must be a directory: {effective_root}")
    mcp = FastMCP(
        f"UpToCode {__version__}",
        instructions=(
            "Bounded architecture-quality analysis for Python agent code. Static analysis "
            "is offline; judgment requires judgment=true and send_code=true."
        ),
        json_response=True,
        stateless_http=mode == "hosted",
        transport_security=transport_security,
    )
    if mode == "hosted":
        def audit_source_hosted(
            source: SourceInput,
            filename: FilenameInput = "snippet.py",
            judgment: JudgmentFlag = False,
            send_code: SendCodeFlag = False,
        ) -> Report:
            """Audit one explicitly submitted Python source document."""
            _hosted_judgment_guard(
                judgment=judgment,
                enabled=hosted_judgment_enabled,
            )
            return audit_source(source, filename, judgment, send_code)

        def audit_diff_hosted(
            diff: DiffInput,
            base_files: BaseFilesInput = None,
            judgment: JudgmentFlag = False,
            send_code: SendCodeFlag = False,
        ) -> Report:
            """Reconstruct and audit explicitly submitted Python diff content."""
            _hosted_judgment_guard(
                judgment=judgment,
                enabled=hosted_judgment_enabled,
            )
            return audit_diff(diff, base_files, judgment, send_code)

        mcp.add_tool(
            audit_source_hosted,
            name="audit_source",
            annotations=READ_ONLY,
        )
        mcp.add_tool(
            audit_diff_hosted,
            name="audit_diff",
            annotations=READ_ONLY,
        )
    else:
        mcp.add_tool(audit_source, annotations=READ_ONLY)
    mcp.add_tool(check_tool_schema, annotations=READ_ONLY)
    mcp.add_tool(check_loop, annotations=READ_ONLY)
    mcp.add_tool(list_rules, annotations=READ_ONLY)
    mcp.add_tool(get_rule, annotations=READ_ONLY)
    mcp.add_tool(review_findings, annotations=READ_ONLY)
    mcp.add_tool(generate_fixplan, annotations=READ_ONLY)

    @mcp.resource("uptocode://rules")
    def rules_resource() -> str:
        """Return the trusted rule catalog as JSON."""
        return list_rules().model_dump_json(indent=2)

    if mode == "local":
        assert effective_root is not None

        def audit_diff_local(
            diff: DiffInput,
            judgment: JudgmentFlag = False,
            send_code: SendCodeFlag = False,
        ) -> Report:
            logger.info("Local diff audit started")
            bases = _workspace_diff_bases(diff, effective_root)
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
                workspace_root=effective_root,
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
            repository = _contained_path(path, effective_root)
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
    """Fail closed if the pinned SDK's private tool-model contract changes."""
    manager = getattr(mcp, "_tool_manager", None)
    registry = getattr(manager, "_tools", None)
    if not isinstance(registry, dict):
        raise RuntimeError(
            "FastMCP strict-schema compatibility failure for installed mcp SDK "
            f"{MCP_SDK_VERSION}: expected _tool_manager._tools mapping"
        )

    argument_models: list[Any] = []
    for name, tool in registry.items():
        metadata = getattr(tool, "fn_metadata", None)
        argument_model = getattr(metadata, "arg_model", None)
        model_config = getattr(argument_model, "model_config", None)
        model_rebuild = getattr(argument_model, "model_rebuild", None)
        model_json_schema = getattr(argument_model, "model_json_schema", None)
        if (
            not isinstance(model_config, dict)
            or not callable(model_rebuild)
            or not callable(model_json_schema)
            or not hasattr(tool, "parameters")
        ):
            raise RuntimeError(
                "FastMCP strict-schema compatibility failure for installed mcp SDK "
                f"{MCP_SDK_VERSION}: tool {name!r} no longer exposes the expected "
                "fn_metadata.arg_model contract"
            )
        argument_models.append(argument_model)

    try:
        for tool, argument_model in zip(registry.values(), argument_models, strict=True):
            argument_model.model_config["extra"] = "forbid"
            argument_model.model_rebuild(force=True)
            tool.parameters = argument_model.model_json_schema()
    except Exception as error:
        raise RuntimeError(
            "FastMCP strict-schema compatibility failure for installed mcp SDK "
            f"{MCP_SDK_VERSION}: private argument-model hardening failed"
        ) from error


server = create_server()


class TokenBucketLimiter:
    """Bounded, in-memory per-credential token bucket using monotonic time."""

    def __init__(
        self,
        rate_per_minute: int = DEFAULT_RATE_LIMIT_PER_MINUTE,
        *,
        max_buckets: int = MAX_RATE_LIMIT_BUCKETS,
        idle_seconds: float = RATE_LIMIT_IDLE_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if rate_per_minute < 1:
            raise ValueError("Hosted rate limit must be at least 1 request per minute")
        if max_buckets < 1 or idle_seconds <= 0:
            raise ValueError("Hosted rate-limit bounds must be positive")
        self.rate_per_minute = rate_per_minute
        self.capacity = float(rate_per_minute)
        self.refill_per_second = float(rate_per_minute) / 60.0
        self.max_buckets = max_buckets
        self.idle_seconds = idle_seconds
        self._clock = clock
        self._buckets: dict[str, tuple[float, float]] = {}
        self._lock = threading.Lock()

    @property
    def bucket_count(self) -> int:
        with self._lock:
            return len(self._buckets)

    def allow(self, credential_digest: str) -> tuple[bool, int]:
        now = self._clock()
        with self._lock:
            stale = [
                key
                for key, (_, last_seen) in self._buckets.items()
                if now - last_seen >= self.idle_seconds
            ]
            for key in stale:
                del self._buckets[key]

            if credential_digest not in self._buckets and len(self._buckets) >= self.max_buckets:
                oldest = min(self._buckets, key=lambda key: self._buckets[key][1])
                del self._buckets[oldest]

            tokens, last_seen = self._buckets.get(
                credential_digest,
                (self.capacity, now),
            )
            elapsed = max(0.0, now - last_seen)
            tokens = min(self.capacity, tokens + elapsed * self.refill_per_second)
            if tokens >= 1.0:
                self._buckets[credential_digest] = (tokens - 1.0, now)
                return True, 0

            self._buckets[credential_digest] = (tokens, now)
            retry_after = max(1, math.ceil((1.0 - tokens) / self.refill_per_second))
            return False, retry_after


class BearerKeyMiddleware:
    """Small payload-blind ASGI authorization boundary for private beta access."""

    def __init__(
        self,
        app: ASGIApplication,
        hashes: set[str],
        rate_limiter: TokenBucketLimiter,
    ) -> None:
        self.app = app
        self.hashes = hashes
        self.rate_limiter = rate_limiter

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
        key_id = "health"

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
                key_id = "unauthorized"
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
            key_id = digest[:KEY_ID_PREFIX_LENGTH]
            allowed, retry_after = self.rate_limiter.allow(digest)
            if not allowed:
                await send_with_correlation(
                    {
                        "type": "http.response.start",
                        "status": 429,
                        "headers": [
                            (b"content-type", b"application/json"),
                            (b"retry-after", str(retry_after).encode("ascii")),
                        ],
                    }
                )
                await send_with_correlation(
                    {"type": "http.response.body", "body": b'{"error":"rate_limited"}'}
                )
                logger.info(
                    "Hosted request completed correlation_id=%s key_id=%s status=%d "
                    "duration_ms=%d",
                    correlation_id,
                    key_id,
                    status,
                    round((time.monotonic() - started) * 1000),
                )
                return
        await self.app(scope, receive, send_with_correlation)
        logger.info(
            "Hosted request completed correlation_id=%s key_id=%s status=%d duration_ms=%d",
            correlation_id,
            key_id,
            status,
            round((time.monotonic() - started) * 1000),
        )


def hosted_app() -> ASGIApplication:
    """Build the stateless hosted ASGI app without path-bearing tools."""
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.routing import Mount, Route

    hashes = {item.strip().lower() for item in os.getenv("UPTOCODE_API_KEY_HASHES", "").split(",") if item.strip()}
    if not hashes:
        raise ValueError("UPTOCODE_API_KEY_HASHES must contain at least one SHA-256 key hash")
    invalid_hash = any(
        len(item) != 64
        or any(character not in "0123456789abcdef" for character in item)
        for item in hashes
    )
    if invalid_hash:
        raise ValueError("UPTOCODE_API_KEY_HASHES must contain only hexadecimal SHA-256 digests")
    rate_limit_raw = os.getenv(
        "UPTOCODE_RATE_LIMIT_PER_MINUTE",
        str(DEFAULT_RATE_LIMIT_PER_MINUTE),
    ).strip()
    try:
        rate_limit = int(rate_limit_raw)
    except ValueError as error:
        raise ValueError("UPTOCODE_RATE_LIMIT_PER_MINUTE must be a positive integer") from error
    if rate_limit < 1:
        raise ValueError("UPTOCODE_RATE_LIMIT_PER_MINUTE must be a positive integer")

    judgment_raw = os.getenv("UPTOCODE_HOSTED_JUDGMENT", "false").strip().lower()
    if judgment_raw not in {"true", "false"}:
        raise ValueError("UPTOCODE_HOSTED_JUDGMENT must be true or false")
    allowed_hosts = [
        item.strip().lower()
        for item in os.getenv("UPTOCODE_HOSTED_ALLOWED_HOSTS", "").split(",")
        if item.strip()
    ]
    invalid_host = any(
        "://" in item or "/" in item or any(character.isspace() for character in item)
        for item in allowed_hosts
    )
    if invalid_host:
        raise ValueError("UPTOCODE_HOSTED_ALLOWED_HOSTS must contain bare host names")
    transport_security = None
    if allowed_hosts:
        transport_security = TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=allowed_hosts,
            allowed_origins=[f"https://{host}" for host in allowed_hosts],
        )
    hosted = create_server(
        mode="hosted",
        hosted_judgment_enabled=judgment_raw == "true",
        transport_security=transport_security,
    )

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
    return BearerKeyMiddleware(
        cast(ASGIApplication, app),
        hashes,
        TokenBucketLimiter(rate_limit),
    )


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
