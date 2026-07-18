from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from archagent_audit.cli import app
from archagent_audit.engine import scan_path
from archagent_audit.models import Report
from archagent_audit.planner import generate_fixplan
from archagent_audit.review import create_manifest, report_fingerprint


ROOT = Path(__file__).parents[1]
runner = CliRunner()


def bad_report() -> Report:
    return scan_path(ROOT / "fixtures" / "bad_python")


def test_manifest_is_bound_to_report_and_explicit_decisions() -> None:
    report = bad_report()
    approved = report.findings[0]
    rejected = report.findings[1]

    manifest = create_manifest(
        report,
        approve={approved.fingerprint},
        reject={rejected.rule_id},
    )

    assert manifest.report_fingerprint == report_fingerprint(report)
    assert [(item.fingerprint, item.status) for item in manifest.decisions] == [
        (approved.fingerprint, "approved"),
        (rejected.fingerprint, "rejected"),
    ]


def test_fixplan_contains_only_approved_findings_and_required_sections() -> None:
    report = bad_report()
    approved = report.findings[0]
    manifest = create_manifest(report, approve={approved.fingerprint})

    plan = generate_fixplan(report, manifest)

    assert approved.fingerprint in plan
    assert report.findings[1].fingerprint not in plan
    for heading in (
        "Objective",
        "Evidence",
        "Likely files",
        "Implementation steps",
        "Acceptance checks",
        "Risks and tradeoffs",
        "Codex prompt",
    ):
        assert heading in plan


def test_fixplan_rejects_manifest_from_different_report() -> None:
    report = bad_report()
    manifest = create_manifest(report, approve_all=True)
    manifest.report_fingerprint = "wrong"

    with pytest.raises(ValueError, match="does not match"):
        generate_fixplan(report, manifest)


def test_review_and_plan_cli_do_not_modify_scanned_source(tmp_path: Path) -> None:
    report = bad_report()
    report_path = tmp_path / "report.json"
    report_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    source = ROOT / "fixtures" / "bad_python" / "agent.py"
    before = source.read_bytes()

    reviewed = runner.invoke(
        app,
        ["review", str(report_path), "--approve-all", "--non-interactive"],
    )
    manifest_path = tmp_path / ".archagent-audit" / "manifest.json"
    planned = runner.invoke(
        app,
        [
            "plan",
            str(report_path),
            "--manifest",
            str(manifest_path),
            "--output",
            str(tmp_path / "FIXPLAN.md"),
        ],
    )

    assert reviewed.exit_code == 0, reviewed.output
    assert manifest_path.exists()
    assert planned.exit_code == 0, planned.output
    assert (tmp_path / "FIXPLAN.md").exists()
    assert source.read_bytes() == before


def test_noninteractive_review_requires_decisions(tmp_path: Path) -> None:
    report_path = tmp_path / "report.json"
    report_path.write_text(bad_report().model_dump_json(), encoding="utf-8")

    result = runner.invoke(app, ["review", str(report_path), "--non-interactive"])

    assert result.exit_code == 2
    assert "decision" in result.output.lower()

