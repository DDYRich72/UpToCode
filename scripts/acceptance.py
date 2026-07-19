"""Cross-platform, offline acceptance runner for the committed ArchAgent MVP."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
CLI = [PYTHON, "-m", "archagent_audit.cli"]


def run(
    command: list[str],
    *,
    expected: int = 0,
    capture: bool = True,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        capture_output=capture,
    )
    if result.returncode != expected:
        detail = f"\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}" if capture else ""
        raise AssertionError(
            f"Expected exit {expected}, got {result.returncode}: {command}{detail}"
        )
    return result


def tracked_status() -> str:
    return run(
        ["git", "status", "--porcelain", "--untracked-files=no"]
    ).stdout.strip()


def tree_digest(path: Path) -> str:
    digest = hashlib.sha256()
    for file in sorted(item for item in path.rglob("*") if item.is_file()):
        digest.update(file.relative_to(path).as_posix().encode())
        digest.update(file.read_bytes())
    return digest.hexdigest()


def parse_report(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


MCP_PROBE = r'''
import asyncio
import json
import sys
from datetime import timedelta
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def payload(result):
    for item in result.content:
        text = getattr(item, "text", None)
        if text:
            return json.loads(text)
    raise AssertionError("MCP result contained no JSON text")


async def main():
    root = Path(sys.argv[1])
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "archagent_audit.mcp_server"],
        cwd=root,
    )
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(
            read, write, read_timeout_seconds=timedelta(seconds=30)
        ) as session:
            await session.initialize()
            tools = await session.list_tools()
            tool_names = sorted(tool.name for tool in tools.tools)
            assert tool_names == [
                "audit_diff",
                "audit_file",
                "audit_repo",
                "audit_source",
                "check_loop",
                "check_tool_schema",
                "generate_fixplan",
                "get_rule",
                "list_rules",
                "review_findings",
            ]
            first = payload(await session.call_tool(
                "check_loop", {"snippet": "while True:\n    work()\n"}
            ))
            assert any(item["rule_id"] == "AA001" for item in first["findings"])
            malformed = await session.call_tool("check_loop", {"wrong": "value"})
            assert malformed.isError
            second = payload(await session.call_tool(
                "audit_diff",
                {"diff": "--- /dev/null\n+++ b/a.py\n@@ -0,0 +1,2 @@\n+while True:\n+    work()\n"},
            ))
            assert any(item["rule_id"] == "AA001" for item in second["findings"])
            print(json.dumps({
                "transport": "stdio",
                "tools": tool_names,
                "check_loop": first,
                "malformed_call_is_error": malformed.isError,
            }, sort_keys=True))


asyncio.run(main())
'''


def main() -> int:
    status_before = tracked_status()
    fixture_before = tree_digest(ROOT / "fixtures")
    run([PYTHON, "-m", "pytest", "-q"], capture=False)

    with tempfile.TemporaryDirectory(prefix="archagent-acceptance-") as temp_name:
        temp = Path(temp_name)
        bad_report_path = temp / "bad-report.json"
        clean_report_path = temp / "clean-report.json"

        run(CLI + ["scan", "fixtures/bad_python", "--format", "json", "--output", str(bad_report_path)])
        bad = parse_report(bad_report_path)
        expected = json.loads(
            (ROOT / "tests" / "golden" / "bad_python_fingerprints.json").read_text(
                encoding="utf-8"
            )
        )
        actual = sorted(item["fingerprint"] for item in bad["findings"])
        assert actual == sorted(expected), "Bad-fixture fingerprints differ from golden"

        run(CLI + ["scan", "fixtures/clean_python", "--format", "json", "--output", str(clean_report_path)])
        clean = parse_report(clean_report_path)
        assert clean["findings"] == [], "Clean fixture produced findings"
        assert clean["analysis_warnings"] == [], "Clean fixture produced analysis warnings"
        run(CLI + ["scan", "fixtures/bad_python", "--fail-on", "critical"], expected=1)
        run(CLI + ["scan", "fixtures/clean_python", "--fail-on", "critical"])

        copied_fixture = temp / "bad-copy"
        shutil.copytree(ROOT / "fixtures" / "bad_python", copied_fixture)
        copied_before = tree_digest(copied_fixture)
        copied_report = temp / "copied-report.json"
        shutil.copy2(bad_report_path, copied_report)
        fingerprints = [item["fingerprint"] for item in bad["findings"]]
        approved, rejected = fingerprints[0], ",".join(fingerprints[1:])
        review_command = CLI + [
            "review", str(copied_report), "--approve", approved, "--non-interactive"
        ]
        if rejected:
            review_command += ["--reject", rejected]
        run(review_command)
        manifest = temp / ".archagent-audit" / "manifest.json"
        fixplan = temp / "FIXPLAN.md"
        run(CLI + ["plan", str(copied_report), "--manifest", str(manifest), "--output", str(fixplan)])
        plan_text = fixplan.read_text(encoding="utf-8")
        assert approved in plan_text
        assert all(item not in plan_text for item in fingerprints[1:])
        assert tree_digest(copied_fixture) == copied_before

        html = temp / "report.html"
        run(CLI + ["scan", "fixtures/bad_python", "--format", "html", "--output", str(html)])
        html_text = html.read_text(encoding="utf-8")
        for marker in ("<!doctype html>", "Findings by category", "Coverage", "AA001", "<style>"):
            assert marker in html_text, f"HTML marker missing: {marker}"

        mcp_probe = run([PYTHON, "-c", MCP_PROBE, str(ROOT)])
        print(f"MCP_PROBE: {mcp_probe.stdout.strip()}")

    self_scan = ROOT / ".archagent-audit" / "self-scan.json"
    self_scan.parent.mkdir(parents=True, exist_ok=True)
    run(CLI + ["scan", ".", "--format", "json", "--output", str(self_scan)])
    assert fixture_before == tree_digest(ROOT / "fixtures"), "Canonical fixtures changed"
    assert tracked_status() == status_before, "Tracked git worktree changed during acceptance"
    print(f"PASS: ArchAgent offline acceptance; self-scan: {self_scan}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
