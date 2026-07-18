from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from archagent_audit.cli import app
from archagent_audit.engine import scan_path
from archagent_audit.models import Report
from archagent_audit.redaction import redact_text


runner = CliRunner()


def write_source(root: Path, source: str, name: str = "agent.py") -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def rule_ids(report: Report) -> list[str]:
    return [finding.rule_id for finding in report.findings]


def test_openai_runner_default_is_bounded(tmp_path: Path) -> None:
    write_source(tmp_path, "result = Runner.run(agent, task)\n")

    report = scan_path(tmp_path)

    assert "AA001" not in rule_ids(report)
    assert report.analysis_warnings == []
    assert report.coverage.frameworks_detected == ["openai-agents"]


def test_openai_runner_explicit_numeric_bound_is_clean(tmp_path: Path) -> None:
    write_source(tmp_path, "result = Runner.run(agent, task, max_turns=10)\n")

    report = scan_path(tmp_path)

    assert "AA001" not in rule_ids(report)


def test_openai_runner_none_disables_limit(tmp_path: Path) -> None:
    write_source(tmp_path, "result = Runner.run(agent, task, max_turns=None)\n")

    report = scan_path(tmp_path)

    aa001 = [finding for finding in report.findings if finding.rule_id == "AA001"]
    assert len(aa001) == 1
    finding = aa001[0]
    assert finding.evidence[0].kind == "explicit-disabled-limit"
    assert finding.file == "agent.py"
    assert finding.line == 1
    assert finding.fingerprint


def test_dynamic_max_turns_is_warning_not_finding(tmp_path: Path) -> None:
    write_source(tmp_path, "result = Runner.run(agent, task, max_turns=settings.limit)\n")

    report = scan_path(tmp_path)

    assert "AA001" not in rule_ids(report)
    assert [warning.code for warning in report.analysis_warnings] == ["AA001_INCONCLUSIVE_BOUND"]


def test_custom_unbounded_loop_is_finding(tmp_path: Path) -> None:
    write_source(tmp_path, "async def run_agent():\n    while True:\n        await agent.step()\n")

    report = scan_path(tmp_path)

    assert rule_ids(report) == ["AA001"]
    assert report.findings[0].evidence[0].kind == "custom-loop-no-exit"


def test_custom_counter_and_break_is_clean(tmp_path: Path) -> None:
    write_source(
        tmp_path,
        "async def run_agent():\n"
        "    turns = 0\n"
        "    while True:\n"
        "        await agent.step()\n"
        "        turns += 1\n"
        "        if turns >= 5:\n"
        "            break\n",
    )

    report = scan_path(tmp_path)

    assert "AA001" not in rule_ids(report)


def test_suppression_honored_and_counted(tmp_path: Path) -> None:
    write_source(
        tmp_path,
        "# archagent-audit: ignore AA001\n"
        "result = Runner.run(agent, task, max_turns=None)\n",
    )

    report = scan_path(tmp_path)

    assert "AA001" not in rule_ids(report)
    assert report.suppressions == 1


def test_report_contract_and_deterministic_content(tmp_path: Path) -> None:
    write_source(tmp_path, "while True:\n    work()\n", "z.py")
    write_source(tmp_path, "while True:\n    work()\n", "a.py")

    first = scan_path(tmp_path)
    second = scan_path(tmp_path)
    parsed = Report.model_validate_json(first.model_dump_json())

    assert parsed.schema_version == "1.0"
    assert [finding.file for finding in first.findings] == ["a.py", "z.py"]
    left = first.model_dump(exclude={"generated_at"})
    right = second.model_dump(exclude={"generated_at"})
    assert left == right


def test_secret_redaction_is_irreversible() -> None:
    secret = "sk-proj-abcdefghijklmnopqrstuvwxyz123456"

    redacted, counts = redact_text(f'token = "{secret}"')

    assert secret not in redacted
    assert "[REDACTED:openai-api-key]" in redacted
    assert counts.secrets == 1


def test_discovery_honors_gitignore_and_default_excludes(tmp_path: Path) -> None:
    write_source(tmp_path, "while True:\n    work()\n", "keep.py")
    write_source(tmp_path, "while True:\n    work()\n", "ignored.py")
    write_source(tmp_path, "while True:\n    work()\n", ".venv/hidden.py")
    (tmp_path / ".gitignore").write_text("ignored.py\n", encoding="utf-8")

    report = scan_path(tmp_path)

    assert [finding.file for finding in report.findings] == ["keep.py"]
    assert report.coverage.files_discovered == 1


def test_cli_json_and_threshold_exit_codes(tmp_path: Path) -> None:
    write_source(tmp_path, "while True:\n    work()\n")

    normal = runner.invoke(app, ["scan", str(tmp_path), "--format", "json"])
    gated = runner.invoke(
        app,
        ["scan", str(tmp_path), "--format", "json", "--fail-on", "critical"],
    )

    assert normal.exit_code == 0
    assert json.loads(normal.stdout)["findings"][0]["rule_id"] == "AA001"
    assert gated.exit_code == 1


def test_cli_invalid_path_and_missing_send_code_exit_two(tmp_path: Path) -> None:
    invalid = runner.invoke(app, ["scan", str(tmp_path / "missing")])
    no_consent = runner.invoke(app, ["scan", str(tmp_path), "--judgment"])

    assert invalid.exit_code == 2
    assert no_consent.exit_code == 2
    assert "--send-code" in no_consent.output
