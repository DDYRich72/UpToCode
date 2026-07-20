"""Verify a deployed hosted MCP without making a paid model call."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / ".uptocode" / "hosted-smoke.json"
SYNTHETIC_SENTINEL = "phase5-sentinel@example.invalid"


def _result_text(result: Any) -> str:
    if hasattr(result, "model_dump"):
        return json.dumps(result.model_dump(mode="json"), sort_keys=True)
    return str(result)


async def verify_hosted(
    *,
    endpoint: str,
    credential: str,
    rate_limit: int,
) -> dict[str, object]:
    """Exercise health, auth, discovery, AA001, judgment gate, and rate limiting."""
    base_url = endpoint.removesuffix("/mcp").rstrip("/")
    headers = {"Authorization": f"Bearer {credential}"}
    async with httpx.AsyncClient(timeout=30, follow_redirects=False) as client:
        # Cloud Run reserves /healthz at its public edge even though the same
        # route remains valid for the container liveness probe. Use the public
        # readiness route for the end-to-end hosted check.
        health = await client.get(f"{base_url}/readyz")
        health.raise_for_status()
        health_payload = health.json()
        if health_payload.get("status") != "ok":
            raise RuntimeError("health endpoint did not report status=ok")

        unauthorized = await client.get(endpoint)
        if unauthorized.status_code != 401:
            raise RuntimeError(f"unauthorized MCP request returned {unauthorized.status_code}")

    async with httpx.AsyncClient(headers=headers, timeout=30) as authorized_client:
        async with streamable_http_client(
            endpoint,
            http_client=authorized_client,
        ) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                names = sorted(tool.name for tool in tools.tools)
                forbidden = {"audit_file", "audit_repo"}.intersection(names)
                if forbidden:
                    raise RuntimeError(f"hosted discovery exposed path tools: {sorted(forbidden)}")
                loop = await session.call_tool(
                    "check_loop",
                    {"snippet": "while True:\n    work()\n"},
                )
                if loop.isError or "AA001" not in _result_text(loop):
                    raise RuntimeError("check_loop did not return AA001")
                judgment = await session.call_tool(
                    "audit_source",
                    {
                        "source": f"# {SYNTHETIC_SENTINEL}\nx = 1\n",
                        "filename": "synthetic.py",
                        "judgment": True,
                        "send_code": True,
                    },
                )
                if not judgment.isError or "UPTOCODE_HOSTED_JUDGMENT" not in _result_text(
                    judgment
                ):
                    raise RuntimeError("hosted judgment was not rejected by the global gate")

    retry_after: str | None = None
    async with httpx.AsyncClient(headers=headers, timeout=30, follow_redirects=False) as client:
        for _ in range(rate_limit + 10):
            response = await client.get(endpoint)
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                break
    if not retry_after or not retry_after.isdigit() or int(retry_after) < 1:
        raise RuntimeError("rate limit did not return 429 with a valid Retry-After")

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "endpoint": endpoint,
        "version": health_payload.get("version"),
        "key_id": hashlib.sha256(credential.encode("utf-8")).hexdigest()[:8],
        "tool_names": names,
        "health": "passed",
        "unauthorized": "passed",
        "aa001": "passed",
        "judgment_gate": "passed",
        "rate_limit": "passed",
        "retry_after": int(retry_after),
        "paid_model_calls": 0,
        "synthetic_sentinel": SYNTHETIC_SENTINEL,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a synthetic, no-paid-call smoke test against hosted UpToCode.",
    )
    parser.add_argument("--endpoint", required=True, help="HTTPS URL ending in /mcp")
    parser.add_argument("--rate-limit", type=int, default=30)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--authorize-live-test",
        action="store_true",
        help="Confirm the operator authorized requests to the live hosted endpoint.",
    )
    arguments = parser.parse_args()
    parsed = urlparse(arguments.endpoint)
    if not arguments.authorize_live_test:
        parser.error("--authorize-live-test is required")
    if parsed.scheme != "https" or not parsed.netloc or not parsed.path.endswith("/mcp"):
        parser.error("--endpoint must be an HTTPS URL ending in /mcp")
    if arguments.rate_limit < 1:
        parser.error("--rate-limit must be positive")
    credential = os.environ.get("UPTOCODE_JUDGE_KEY", "")
    if not credential:
        parser.error("UPTOCODE_JUDGE_KEY is required")

    try:
        evidence = asyncio.run(
            verify_hosted(
                endpoint=arguments.endpoint,
                credential=credential,
                rate_limit=arguments.rate_limit,
            )
        )
        output = arguments.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    except (OSError, RuntimeError, httpx.HTTPError) as error:
        parser.error(str(error))
    print(f"PASS: hosted no-paid-call smoke; evidence: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
