from __future__ import annotations

import asyncio
import hashlib
from importlib.metadata import version as package_version
import json
from pathlib import Path
from typing import cast

import pytest

from scripts import compliance
import uptocode.mcp_server as mcp_module
from uptocode import __version__
from uptocode.mcp_server import (
    MCP_FASTMCP_COMPAT_VERSION,
    MCP_SDK_VERSION,
    ASGIApplication,
    BearerKeyMiddleware,
    TokenBucketLimiter,
    _harden_tool_contracts,
    create_server,
    hosted_app,
)
from uptocode.models import Report


def test_fastmcp_sdk_upgrade_canary_and_private_contract() -> None:
    import tomllib

    assert package_version("mcp") == MCP_FASTMCP_COMPAT_VERSION
    assert MCP_SDK_VERSION == MCP_FASTMCP_COMPAT_VERSION
    project = tomllib.loads(
        (Path(__file__).parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    )
    assert f"mcp=={MCP_FASTMCP_COMPAT_VERSION}" in project["project"]["dependencies"]
    tools = asyncio.run(create_server().list_tools())
    assert tools
    assert all(tool.inputSchema.get("additionalProperties") is False for tool in tools)


def test_fastmcp_private_contract_change_fails_closed_with_version() -> None:
    class IncompatibleFastMCP:
        pass

    with pytest.raises(RuntimeError, match=rf"installed mcp SDK {MCP_SDK_VERSION}"):
        _harden_tool_contracts(cast(object, IncompatibleFastMCP()))  # type: ignore[arg-type]

    class BrokenManager:
        _tools = {"broken": object()}

    class ChangedToolContract:
        _tool_manager = BrokenManager()

    with pytest.raises(RuntimeError, match="tool 'broken'"):
        _harden_tool_contracts(cast(object, ChangedToolContract()))  # type: ignore[arg-type]


def test_local_server_resolves_root_once_and_contains_every_path_tool(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "inside.py").write_text("x = 1\n", encoding="utf-8")
    outside = tmp_path / "outside.py"
    outside.write_text("x = 1\n", encoding="utf-8")
    server = create_server(workspace_root=workspace)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    class ProgressContext:
        async def report_progress(
            self,
            progress: float,
            total: float | None = None,
            message: str | None = None,
        ) -> None:
            assert progress >= 0

    tools = server._tool_manager._tools

    async def exercise() -> None:
        context = ProgressContext()
        assert await tools["audit_file"].fn(path="inside.py", ctx=context)
        assert await tools["audit_repo"].fn(path=".", ctx=context)
        assert tools["audit_diff"].fn(
            diff=(
                "--- a/inside.py\n"
                "+++ b/inside.py\n"
                "@@ -1 +1,2 @@\n"
                " x = 1\n"
                "+y = 2\n"
            )
        )
        with pytest.raises(Exception, match="outside"):
            await tools["audit_file"].fn(path=str(outside), ctx=context)
        with pytest.raises(Exception, match="outside"):
            await tools["audit_repo"].fn(path=str(tmp_path), ctx=context)
        with pytest.raises(Exception, match="contained"):
            tools["audit_diff"].fn(
                diff="--- ../outside.py\n+++ b/outside.py\n",
            )

    asyncio.run(exercise())


def test_check_tool_schema_has_no_unused_judgment_arguments() -> None:
    tools = asyncio.run(create_server().list_tools())
    schema_tool = next(tool for tool in tools if tool.name == "check_tool_schema")

    assert set(schema_tool.inputSchema["properties"]) == {"schema_json"}


def test_token_bucket_refills_monotonically_and_evicts_bounded_idle_keys() -> None:
    now = [100.0]
    limiter = TokenBucketLimiter(
        2,
        max_buckets=2,
        idle_seconds=60,
        clock=lambda: now[0],
    )

    assert limiter.allow("a") == (True, 0)
    assert limiter.allow("a") == (True, 0)
    assert limiter.allow("a") == (False, 30)
    now[0] += 30
    assert limiter.allow("a") == (True, 0)
    assert limiter.allow("b")[0] is True
    assert limiter.allow("c")[0] is True
    assert limiter.bucket_count == 2
    now[0] += 61
    assert limiter.allow("d")[0] is True
    assert limiter.bucket_count == 1


def test_hosted_middleware_returns_429_and_retry_after_per_key() -> None:
    token = "synthetic-rate-limit-key"
    digest = hashlib.sha256(token.encode()).hexdigest()
    now = [50.0]
    limiter = TokenBucketLimiter(1, clock=lambda: now[0])

    async def application(scope, receive, send) -> None:  # type: ignore[no-untyped-def]
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    middleware = BearerKeyMiddleware(
        cast(ASGIApplication, application),
        {digest},
        limiter,
    )

    async def request() -> list[dict[str, object]]:
        sent: list[dict[str, object]] = []

        async def receive() -> dict[str, object]:
            return {"type": "http.disconnect"}

        async def send(message: dict[str, object]) -> None:
            sent.append(message)

        await middleware(
            {
                "type": "http",
                "path": "/mcp",
                "headers": [(b"authorization", f"Bearer {token}".encode())],
            },
            receive,
            send,
        )
        return sent

    first = asyncio.run(request())
    second = asyncio.run(request())
    first_start = next(item for item in first if item["type"] == "http.response.start")
    second_start = next(item for item in second if item["type"] == "http.response.start")

    assert first_start["status"] == 200
    assert second_start["status"] == 429
    assert (b"retry-after", b"60") in second_start["headers"]
    assert any(item.get("body") == b'{"error":"rate_limited"}' for item in second)


def test_hosted_judgment_is_rejected_until_global_gate_is_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[bool, bool]] = []

    def fake_scan_sources(
        sources: dict[str, str],
        *,
        judgment: bool = False,
        send_code: bool = False,
    ) -> Report:
        assert sources
        calls.append((judgment, send_code))
        return Report(scan_root="<submitted-code>")

    monkeypatch.setattr(mcp_module, "_scan_sources", fake_scan_sources)
    disabled = create_server(mode="hosted")
    enabled = create_server(mode="hosted", hosted_judgment_enabled=True)

    async def exercise() -> None:
        with pytest.raises(Exception, match="UPTOCODE_HOSTED_JUDGMENT"):
            await disabled.call_tool(
                "audit_source",
                {"source": "x = 1", "judgment": True, "send_code": True},
            )
        assert await enabled.call_tool(
            "audit_source",
            {"source": "x = 1", "judgment": True, "send_code": True},
        )

    asyncio.run(exercise())
    assert calls == [(True, True)]


def test_hosted_environment_controls_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    token = "synthetic-hosted-key"
    monkeypatch.setenv("UPTOCODE_API_KEY_HASHES", hashlib.sha256(token.encode()).hexdigest())
    monkeypatch.setenv("UPTOCODE_RATE_LIMIT_PER_MINUTE", "0")
    with pytest.raises(ValueError, match="positive integer"):
        hosted_app()

    monkeypatch.setenv("UPTOCODE_RATE_LIMIT_PER_MINUTE", "30")
    monkeypatch.setenv("UPTOCODE_HOSTED_JUDGMENT", "sometimes")
    with pytest.raises(ValueError, match="true or false"):
        hosted_app()

    monkeypatch.delenv("UPTOCODE_HOSTED_JUDGMENT")
    application = hosted_app()
    assert isinstance(application, BearerKeyMiddleware)
    assert application.rate_limiter.rate_per_minute == 30


def test_package_runtime_and_server_manifest_versions_agree() -> None:
    import tomllib

    root = Path(__file__).parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    manifest = json.loads((root / "server.json").read_text(encoding="utf-8"))
    package_versions = {item["version"] for item in manifest["packages"]}

    assert project["project"]["version"] == __version__
    assert manifest["version"] == __version__
    assert package_versions == {__version__}
    assert package_version("uptocode") == __version__


def test_compliance_version_contract_rejects_installed_metadata_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert compliance.version_contract()["status"] == "passed"

    monkeypatch.setattr(compliance.importlib.metadata, "version", lambda _: "0.0.0")
    contract = compliance.version_contract()

    assert contract["installed_metadata"] == "0.0.0"
    assert contract["status"] == "failed"


def test_compliance_version_contract_rejects_missing_distribution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing(_: str) -> str:
        raise compliance.importlib.metadata.PackageNotFoundError

    monkeypatch.setattr(compliance.importlib.metadata, "version", missing)
    contract = compliance.version_contract()

    assert contract["installed_metadata"] is None
    assert contract["status"] == "failed"
