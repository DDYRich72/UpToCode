from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from uptocode.cli import app
from uptocode.engine import scan_path
from uptocode.reporters.html import render_html


ROOT = Path(__file__).parents[1]
runner = CliRunner()


def test_html_is_standalone_semantic_and_redacted() -> None:
    report = scan_path(ROOT / "fixtures" / "bad_python")

    rendered = render_html(report)

    assert rendered.startswith("<!doctype html>")
    assert "UpToCode architecture report" in rendered
    assert "Findings by category" in rendered
    assert "Coverage" in rendered
    assert "Judgment: not-requested" in rendered
    assert "AA001" in rendered
    assert "Observed:" in rendered
    assert "Tradeoff:" in rendered
    assert "Remediation complexity:" in rendered
    assert "https://" in rendered
    assert "<style>" in rendered
    assert "<script src=" not in rendered
    assert "sk-proj-abcdefghijklmnopqrstuvwxyz123456" not in rendered
    assert "quality score" not in rendered.lower()


def test_html_escapes_source_excerpt(tmp_path: Path) -> None:
    (tmp_path / "agent.py").write_text(
        "while True:\n    work('<script>alert(1)</script>')\n",
        encoding="utf-8",
    )

    rendered = render_html(scan_path(tmp_path))

    assert "<script>alert(1)</script>" not in rendered
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in rendered


def test_cli_writes_html_and_requires_output(tmp_path: Path) -> None:
    (tmp_path / "agent.py").write_text("while True:\n    work()\n", encoding="utf-8")
    output = tmp_path / "report.html"

    missing = runner.invoke(app, ["scan", str(tmp_path), "--format", "html"])
    written = runner.invoke(
        app,
        ["scan", str(tmp_path), "--format", "html", "--output", str(output)],
    )

    assert missing.exit_code == 2
    assert "--output" in missing.output
    assert written.exit_code == 0, written.output
    assert output.read_text(encoding="utf-8").startswith("<!doctype html>")


def test_scan_output_write_failure_is_exit_two(tmp_path: Path) -> None:
    (tmp_path / "agent.py").write_text("print('ok')\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["scan", str(tmp_path), "--format", "json", "--output", str(tmp_path)],
    )

    assert result.exit_code == 2
    assert "Could not write output" in result.output
