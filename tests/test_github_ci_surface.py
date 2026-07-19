from __future__ import annotations

import json
import re
from pathlib import Path

import yaml
from typer.testing import CliRunner

from archagent_audit.cli import app
from archagent_audit.engine import scan_path
from archagent_audit.models import AnalysisWarning
from archagent_audit.reporters.github import (
    MAX_SUMMARY_FINDINGS,
    escape_command_data,
    escape_command_property,
    render_github,
    render_github_summary,
)
from archagent_audit.reporters.sarif import render_sarif


ROOT = Path(__file__).parents[1]


def _finding_report(tmp_path: Path):  # type: ignore[no-untyped-def]
    source = tmp_path / "loop.py"
    source.write_text("while True:\n    work()\n", encoding="utf-8")
    return scan_path(source)


def test_github_workflow_commands_escape_hostile_data(tmp_path: Path) -> None:
    report = _finding_report(tmp_path)
    finding = report.findings[0]
    finding.file = "agent:bad,%\r\n.py"
    finding.rule_id = "AA001:bad,rule"
    finding.verdict.observed = "unsafe%\r\n::error file=owned.py::injected"

    rendered = render_github(report)

    assert escape_command_data("%\r\n") == "%25%0D%0A"
    assert escape_command_property(":,%\r\n") == "%3A%2C%25%0D%0A"
    assert "file=agent%3Abad%2C%25%0D%0A.py" in rendered
    assert "title=AA001%3Abad%2Crule" in rendered
    assert "unsafe%25%0D%0A::error file=owned.py::injected" in rendered
    assert rendered.count("\n") == 0


def test_github_summary_is_bounded_and_markdown_safe(tmp_path: Path) -> None:
    report = _finding_report(tmp_path)
    original = report.findings[0]
    report.findings = []
    for index in range(MAX_SUMMARY_FINDINGS + 3):
        finding = original.model_copy(deep=True)
        finding.file = f"path|{index}.py"
        finding.fingerprint = f"fingerprint-{index}"
        report.findings.append(finding)
    report.analysis_warnings = [
        AnalysisWarning(code="WARN", message="message|with\nnewline")
    ]

    rendered = render_github_summary(report)

    assert "Coverage:" in rendered
    assert "| Critical | 23 |" in rendered
    assert rendered.count("| critical | AA001 |") == MAX_SUMMARY_FINDINGS
    assert "3 additional findings omitted" in rendered
    assert "path\\|0.py" in rendered
    assert "message\\|with newline" in rendered


def test_cli_appends_explicit_and_environment_github_summaries(tmp_path: Path) -> None:
    source = tmp_path / "loop.py"
    source.write_text("while True:\n    work()\n", encoding="utf-8")
    explicit = tmp_path / "explicit.md"
    automatic = tmp_path / "automatic.md"
    runner = CliRunner()

    explicit_result = runner.invoke(
        app,
        ["scan", str(source), "--github-summary", str(explicit)],
    )
    automatic_result = runner.invoke(
        app,
        ["scan", str(source)],
        env={"GITHUB_STEP_SUMMARY": str(automatic)},
    )

    assert explicit_result.exit_code == 0
    assert automatic_result.exit_code == 0
    assert explicit.read_text(encoding="utf-8").startswith("# ArchAgent scan summary")
    assert automatic.read_text(encoding="utf-8").startswith("# ArchAgent scan summary")


def test_sarif_has_no_null_and_declares_rule_default_levels(tmp_path: Path) -> None:
    report = _finding_report(tmp_path)
    report.findings[0].citations = []

    rendered = render_sarif(report)
    payload = json.loads(rendered)
    rule = payload["runs"][0]["tool"]["driver"]["rules"][0]
    result = payload["runs"][0]["results"][0]

    assert "null" not in rendered
    assert "helpUri" not in rule
    assert rule["defaultConfiguration"] == {"level": "error"}
    assert result["partialFingerprints"]["archagentFinding"] == report.findings[0].fingerprint


def test_ci_contract_separates_audit_and_covers_product_surfaces() -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
    jobs = workflow["jobs"]

    assert workflow["concurrency"]["cancel-in-progress"] is True
    assert set(jobs["python"]["strategy"]["matrix"]["os"]) == {
        "ubuntu-latest",
        "windows-latest",
        "macos-latest",
    }
    assert jobs["python"]["strategy"]["matrix"]["python"] == ["3.11", "3.12", "3.13"]
    assert all("timeout-minutes" in job for job in jobs.values())

    python_runs = "\n".join(
        str(step.get("run", "")) for step in jobs["python"]["steps"]
    )
    audit_runs = "\n".join(
        str(step.get("run", "")) for step in jobs["dependency-audit"]["steps"]
    )
    site_runs = "\n".join(
        str(step.get("run", "")) for step in jobs["package-and-site"]["steps"]
    )
    container_runs = "\n".join(
        str(step.get("run", "")) for step in jobs["container-smoke"]["steps"]
    )

    assert "pip_audit" not in python_runs
    assert "dist/archagent_audit-*.whl" in audit_runs
    assert "audit-venv/bin/python -m pip install --upgrade pip setuptools wheel" in audit_runs
    assert "npm run lint" in site_runs
    assert "tsc -- --noEmit" in site_runs
    assert "archagent.sarif" in site_runs
    assert "/healthz" in container_runs
    assert "/mcp" in container_runs and '"401"' in container_runs
    assert "docker stop --time 10" in container_runs
    assert sum(
        1
        for job in jobs.values()
        for step in job["steps"]
        if "actions/upload-artifact@" in str(step.get("uses", ""))
    ) >= 3


def test_composite_action_uploads_sarif_before_returning_scan_failure() -> None:
    action = yaml.safe_load((ROOT / "action.yml").read_text(encoding="utf-8"))

    assert set(action["inputs"]) == {"path", "fail-on", "version", "upload-sarif"}
    assert action["inputs"]["version"]["default"] == "source"
    steps = action["runs"]["steps"]
    names = [step["name"] for step in steps]
    upload_index = names.index("Upload SARIF before returning scanner failure")
    return_index = names.index("Return scanner exit code")

    assert upload_index < return_index
    assert "always()" in steps[upload_index]["if"]
    assert "exit 0" in steps[names.index("Scan and preserve exit code")]["run"]
    assert "steps.scan.outputs.exit-code" in steps[return_index]["env"]["ARCHAGENT_SCANNER_EXIT_CODE"]
    assert 'archagent-audit==${ARCHAGENT_ACTION_VERSION}' in steps[1]["run"]


def test_external_actions_are_sha_pinned_and_dependabot_is_weekly() -> None:
    action_files = [ROOT / "action.yml", *sorted((ROOT / ".github/workflows").glob("*.yml"))]
    uses_line = re.compile(r"^\s*-?\s*uses:\s*[^\s]+@([0-9a-f]{40})\s+#\s+\S+\s*$")

    for path in action_files:
        for line in path.read_text(encoding="utf-8").splitlines():
            if re.match(r"^\s*-?\s*uses:", line):
                assert uses_line.match(line), f"Unpinned action in {path.name}: {line}"

    dependabot = yaml.safe_load(
        (ROOT / ".github/dependabot.yml").read_text(encoding="utf-8")
    )
    assert {item["package-ecosystem"] for item in dependabot["updates"]} == {
        "github-actions",
        "pip",
        "npm",
    }
    assert all(item["schedule"]["interval"] == "weekly" for item in dependabot["updates"])


def test_release_workflow_retains_artifacts_without_publishing() -> None:
    release = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")

    assert "upload-artifact@" in release
    assert "attest-build-provenance@" in release
    assert "gh-action-pypi-publish" not in release
    assert "PyPI publication is intentionally absent" in release
