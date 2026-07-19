from __future__ import annotations

import asyncio
import hashlib
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import timedelta

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


def _available_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _wait_for_health(url: str, process: subprocess.Popen[str]) -> None:
    for _ in range(100):
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            raise AssertionError(f"Hosted MCP exited early.\n{stdout}\n{stderr}")
        try:
            with urllib.request.urlopen(url, timeout=1) as response:  # noqa: S310
                if response.status == 200:
                    return
        except (OSError, urllib.error.URLError):
            time.sleep(0.05)
    raise AssertionError("Hosted MCP did not become healthy")


def test_real_streamable_http_lifecycle_and_authorization() -> None:
    token = "synthetic-private-beta-key"
    port = _available_port()
    environment = {
        **os.environ,
        "ARCHAGENT_API_KEY_HASHES": hashlib.sha256(token.encode()).hexdigest(),
    }
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "archagent_audit.mcp_server:hosted_app",
            "--factory",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        _wait_for_health(f"http://127.0.0.1:{port}/healthz", process)

        async def exercise() -> None:
            async with httpx.AsyncClient(
                headers={"Authorization": f"Bearer {token}"}, timeout=10
            ) as client:
                async with streamable_http_client(
                    f"http://127.0.0.1:{port}/mcp", http_client=client
                ) as (read, write, _):
                    async with ClientSession(
                        read,
                        write,
                        read_timeout_seconds=timedelta(seconds=10),
                    ) as session:
                        await session.initialize()
                        tools = await session.list_tools()
                        names = {tool.name for tool in tools.tools}
                        assert "audit_source" in names
                        assert "audit_file" not in names
                        result = await session.call_tool(
                            "check_loop", {"snippet": "while True:\n    work()\n"}
                        )
                        assert result.isError is False

            async def one_request(_: int) -> bool:
                async with httpx.AsyncClient(
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=20,
                ) as client:
                    response = await client.get(f"http://127.0.0.1:{port}/healthz")
                    return response.status_code == 200 and response.json()["status"] == "ok"

            concurrent = await asyncio.gather(*(one_request(index) for index in range(4)))
            assert all(concurrent)

        asyncio.run(exercise())

        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/mcp", timeout=2)  # noqa: S310
        except urllib.error.HTTPError as error:
            assert error.code == 401
        else:
            raise AssertionError("Hosted MCP accepted a request without authorization")
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
