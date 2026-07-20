from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from uptocode.cli import app
from uptocode.engine import scan_path
from uptocode.reporters.terminal import render_terminal


ROOT = Path(__file__).parents[1]
runner = CliRunner()


def test_bad_fixture_exercises_static_rulepack_without_leaking_secret() -> None:
    report = scan_path(ROOT / "fixtures" / "bad_python")
    ids = {finding.rule_id for finding in report.findings}

    assert ids == {"AA001", "AA002", "AA003", "AA004", "AA006", "AA007", "AA010", "AA011", "AA012", "AA013"}
    serialized = report.model_dump_json()
    assert "sk-proj-abcdefghijklmnopqrstuvwxyz123456" not in serialized
    assert "[REDACTED:openai-api-key]" in serialized


def test_clean_fixture_has_no_findings_or_unexplained_warnings() -> None:
    report = scan_path(ROOT / "fixtures" / "clean_python")

    assert report.findings == []
    assert report.analysis_warnings == []


def test_hardcoded_pii_is_reported_and_redacted(tmp_path: Path) -> None:
    (tmp_path / "agent.py").write_text(
        'contact = "owner@example.com"\nagent = Agent(name="support")\n',
        encoding="utf-8",
    )

    report = scan_path(tmp_path)
    rendered = report.model_dump_json()

    assert any(item.rule_id == "AA006" for item in report.findings)
    assert "owner@example.com" not in rendered
    assert "[REDACTED:email-address]" in rendered
    assert report.redactions.pii >= 1


@pytest.mark.parametrize(
    ("source", "expected_rule"),
    [
        ('client.responses.create(model="gpt", input="x")', "AA002"),
        ('@function_tool\ndef delete_user(value):\n    database.delete(value)', "AA003"),
        ('@function_tool\ndef tool(arg):\n    subprocess.run(arg)', "AA004"),
        ('API_KEY="sk-proj-abcdefghijklmnopqrstuvwxyz123456"\nprompt=f"{API_KEY}"', "AA006"),
        ('client.responses.create(model="gpt", input="x")', "AA007"),
        ('save(response.output_text)', "AA010"),
        ('agent = Agent(name="x")', "AA011"),
        ('agent = Agent(name="x")', "AA012"),
    ],
)
def test_static_rule_positive_cases(tmp_path: Path, source: str, expected_rule: str) -> None:
    (tmp_path / "agent.py").write_text(source + "\n", encoding="utf-8")

    report = scan_path(tmp_path)

    assert expected_rule in {finding.rule_id for finding in report.findings}


def test_rule_suppression_is_generic(tmp_path: Path) -> None:
    (tmp_path / "agent.py").write_text(
        "@function_tool  # uptocode: ignore AA004\n"
        "def tool(model_arg):\n"
        "    subprocess.run(model_arg)\n",
        encoding="utf-8",
    )

    report = scan_path(tmp_path)

    assert "AA004" not in {finding.rule_id for finding in report.findings}
    assert report.suppressions == 1


def test_parse_error_warns_and_continues(tmp_path: Path) -> None:
    (tmp_path / "broken.py").write_text("def nope(:\n", encoding="utf-8")
    (tmp_path / "good.py").write_text("while True:\n    work()\n", encoding="utf-8")

    report = scan_path(tmp_path)

    assert "AA001" in {finding.rule_id for finding in report.findings}
    assert "PYTHON_PARSE_ERROR" in {warning.code for warning in report.analysis_warnings}


def test_cli_returns_two_when_no_discovered_python_file_can_be_parsed(tmp_path: Path) -> None:
    (tmp_path / "broken.py").write_text("def nope(:\n", encoding="utf-8")

    result = runner.invoke(app, ["scan", str(tmp_path)])

    assert result.exit_code == 2
    assert "No discovered Python file could be analyzed" in result.output


def test_custom_exclude_and_size_limit_are_reported(tmp_path: Path) -> None:
    (tmp_path / ".uptocode.yml").write_text(
        "exclude:\n  - excluded.py\nmax_file_size: 20\n",
        encoding="utf-8",
    )
    (tmp_path / "excluded.py").write_text("while True:\n    work()\n", encoding="utf-8")
    (tmp_path / "large.py").write_text("#" * 30, encoding="utf-8")

    report = scan_path(tmp_path)

    assert report.coverage.files_discovered == 0
    assert report.coverage.files_skipped == 2


def test_generated_and_binary_python_files_are_excluded(tmp_path: Path) -> None:
    (tmp_path / "generated").mkdir()
    (tmp_path / "generated" / "agent.py").write_text(
        "while True:\n    work()\n", encoding="utf-8"
    )
    (tmp_path / "schema_pb2.py").write_text(
        "while True:\n    work()\n", encoding="utf-8"
    )
    (tmp_path / "binary.py").write_bytes(b"while True:\x00\n")

    report = scan_path(tmp_path)

    assert report.coverage.files_discovered == 0
    assert report.coverage.files_skipped == 3
    assert report.analysis_warnings == []


def test_terminal_report_is_human_readable_and_redacted() -> None:
    report = scan_path(ROOT / "fixtures" / "bad_python")

    rendered = render_terminal(report)

    assert "UpToCode" in rendered
    assert "AA001" in rendered
    assert "Coverage" in rendered
    assert "sk-proj-abcdefghijklmnopqrstuvwxyz123456" not in rendered


def test_empty_and_no_agent_repositories_are_truthful(tmp_path: Path) -> None:
    empty = scan_path(tmp_path)
    (tmp_path / "plain.py").write_text("print('hello')\n", encoding="utf-8")
    plain = scan_path(tmp_path)

    assert empty.findings == []
    assert empty.coverage.files_analyzed == 0
    assert plain.findings == []
    assert plain.coverage.files_analyzed == 1
    assert plain.coverage.rules_not_applicable


def test_terminal_cli_uses_terminal_renderer(tmp_path: Path) -> None:
    (tmp_path / "agent.py").write_text("while True:\n    work()\n", encoding="utf-8")

    result = runner.invoke(app, ["scan", str(tmp_path)])

    assert result.exit_code == 0
    assert "UpToCode scan" in result.stdout
