from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from uptocode.baseline import apply_baseline, create_baseline, load_baseline
from uptocode.cli import app
from uptocode.engine import scan_path
from uptocode.models import (
    AnalysisWarning,
    Citation,
    Coverage,
    Evidence,
    Finding,
    Remediation,
    Report,
    Severity,
    Verdict,
)
from uptocode.reporters.github import render_github
from uptocode.reporters.html import render_html
from uptocode.reporters.sarif import render_sarif
from uptocode.reporters.terminal import render_terminal
from uptocode.rules.registry import core_rule_map
from uptocode.share_safe import make_share_safe
from uptocode.suppressions import parse_suppressions


def write_source(tmp_path: Path, source: str) -> Report:
    (tmp_path / "agent.py").write_text(source, encoding="utf-8")
    return scan_path(tmp_path)


def aa013_source(*, setup: str = "history = []", truncation: str = "") -> str:
    return (
        "from openai import OpenAI\n"
        "client = OpenAI(timeout=30, max_retries=2)\n"
        f"{setup}\n"
        "for item in items:\n"
        "    history.append(item)\n"
        f"    {truncation}\n" if truncation else
        "from openai import OpenAI\n"
        "client = OpenAI(timeout=30, max_retries=2)\n"
        f"{setup}\n"
        "for item in items:\n"
        "    history.append(item)\n"
    ) + "    client.responses.create(input=history, max_output_tokens=10)\n"


def test_aa013_positive_and_suppression(tmp_path: Path) -> None:
    positive = write_source(tmp_path, aa013_source())
    assert [item.title for item in positive.findings if item.rule_id == "AA013"] == [
        "Unbounded context growth"
    ]

    suppressed_source = aa013_source().replace(
        "for item in items:", "# uptocode: ignore AA013\nfor item in items:"
    )
    suppressed = write_source(tmp_path, suppressed_source)
    assert not [item for item in suppressed.findings if item.rule_id == "AA013"]
    assert suppressed.suppressions >= 1


@pytest.mark.parametrize(
    ("setup", "truncation"),
    [
        ("history = []", "history = history[-10:]"),
        ("history = []", "history[:] = history[-10:]"),
        ("history = []", "del history[:1]"),
        ("history = []", "history.pop(0)"),
        ("from collections import deque\nhistory = deque()", "history.popleft()"),
        ("from collections import deque\nhistory = deque(maxlen=10)", ""),
    ],
)
def test_aa013_recognized_truncation_is_clean(
    tmp_path: Path, setup: str, truncation: str
) -> None:
    report = write_source(tmp_path, aa013_source(setup=setup, truncation=truncation))
    assert not [item for item in report.findings if item.rule_id == "AA013"]


def test_aa013_inconclusive_and_alias_false_positive(tmp_path: Path) -> None:
    inconclusive = write_source(
        tmp_path,
        "for item in items:\n"
        "    history.append(item)\n"
        "    client.responses.create(input=history)\n",
    )
    assert "AA013_INCONCLUSIVE_CONTEXT_GROWTH" in {
        item.code for item in inconclusive.analysis_warnings
    }
    alias = write_source(
        tmp_path,
        "history = []\nother = []\nfor item in items:\n"
        "    history.append(item)\n    client.responses.create(input=other)\n",
    )
    assert not [item for item in alias.findings if item.rule_id == "AA013"]


def test_aa007_retry_without_backoff_and_recognized_backoff(tmp_path: Path) -> None:
    missing = write_source(
        tmp_path,
        "client = OpenAI(timeout=30, retry=True)\n"
        "client.responses.create(input='x', max_output_tokens=10)\n",
    )
    assert "Retry policy lacks backoff" in {
        item.title for item in missing.findings if item.rule_id == "AA007"
    }
    clean = write_source(
        tmp_path,
        "@retry(wait=wait_exponential(multiplier=1))\n"
        "def run():\n"
        "    client.responses.create(input='x', timeout=30, retry=True, max_output_tokens=10)\n",
    )
    assert "Retry policy lacks backoff" not in {
        item.title for item in clean.findings if item.rule_id == "AA007"
    }


def test_registry_citations_are_complete_and_cross_vendor(tmp_path: Path) -> None:
    report = write_source(
        tmp_path,
        "@function_tool\ndef lookup(value):\n    subprocess.run(value)\n",
    )
    finding = next(item for item in report.findings if item.rule_id == "AA004")
    expected = [item.to_public() for item in core_rule_map()["AA004"].citations]
    assert finding.citations == expected
    assert {item.publisher for item in finding.citations} >= {"OpenAI", "Anthropic"}
    assert "Primary guidance" not in report.model_dump_json()
    assert Citation(vendor="Legacy", title="Old", url="https://example.com").publisher == "Legacy"
    bad = scan_path(Path(__file__).parents[1] / "fixtures" / "bad_python")
    registry = core_rule_map()
    assert all(
        item.citations == [citation.to_public() for citation in registry[item.rule_id].citations]
        for item in bad.findings
    )


def test_baseline_three_scan_lifecycle_and_legacy_loader(tmp_path: Path) -> None:
    start = datetime(2026, 7, 1, tzinfo=timezone.utc)
    report = write_source(tmp_path, "while True:\n    work()\n")
    baseline = create_baseline(report, now=start)
    fingerprint = report.findings[0].fingerprint

    persisted = write_source(tmp_path, "while True:\n    work()\n")
    persisted_findings = list(persisted.findings)
    persisted, existing = apply_baseline(
        persisted, baseline, findings=persisted_findings, now=start + timedelta(days=5)
    )
    assert existing and persisted.coverage.baseline_findings == 1
    assert persisted.baseline_debt.aging[0].age_days == 5
    updated = create_baseline(
        persisted,
        previous=baseline,
        findings=persisted_findings,
        now=start + timedelta(days=5),
    )
    assert updated.entries[0].first_seen == start

    (tmp_path / "agent.py").write_text("x = 1\n", encoding="utf-8")
    resolved = scan_path(tmp_path)
    resolved, _ = apply_baseline(resolved, updated, now=start + timedelta(days=6))
    assert resolved.coverage.baseline_resolved == 1
    assert fingerprint in {item.fingerprint for item in resolved.baseline_debt.resolved}

    legacy = load_baseline(
        json.dumps(
            {
                "schema_version": "2.0",
                "created_at": start.isoformat(),
                "fingerprints": [fingerprint],
            }
        )
    )
    assert legacy.entries[0].first_seen == start


def test_cli_combined_baseline_update_preserves_first_seen(tmp_path: Path) -> None:
    target = tmp_path / "agent.py"
    target.write_text("while True:\n    work()\n", encoding="utf-8")
    baseline_path = tmp_path / "baseline.json"
    runner = CliRunner()
    seeded = runner.invoke(
        app, ["scan", str(target), "--update-baseline", str(baseline_path)]
    )
    assert seeded.exit_code == 0
    baseline = load_baseline(baseline_path.read_text(encoding="utf-8"))
    original_first_seen = baseline.entries[0].first_seen
    combined = runner.invoke(
        app,
        [
            "scan",
            str(target),
            "--format",
            "json",
            "--baseline",
            str(baseline_path),
            "--update-baseline",
            str(baseline_path),
        ],
    )
    assert combined.exit_code == 0
    assert json.loads(combined.stdout)["coverage"]["baseline_findings"] == 1
    updated = load_baseline(baseline_path.read_text(encoding="utf-8"))
    assert updated.entries[0].first_seen == original_first_seen


def test_suppression_metadata_expiry_boundary_and_malformed() -> None:
    today = date(2026, 7, 20)
    lines = [
        '# uptocode: ignore AA001 owner=team reason="migration" expires=2026-07-19',
        '# uptocode: ignore AA002 owner=team reason="migration" expires=2026-07-20',
        '# uptocode: ignore AA003 owner=team reason="migration" expires=2026-07-21',
        '# uptocode: ignore AA004 reason=missing-quotes',
    ]
    index, warnings = parse_suppressions(lines, file="agent.py", today=today)
    assert index.find("AA001", 1) and not index.find("AA001", 1).active  # type: ignore[union-attr]
    assert index.find("AA002", 2) and index.find("AA002", 2).active  # type: ignore[union-attr]
    assert index.find("AA003", 3) and index.find("AA003", 3).active  # type: ignore[union-attr]
    assert index.find("AA004", 4).detail.reason is None  # type: ignore[union-attr]
    assert {item.code for item in warnings} == {
        "SUPPRESSION_EXPIRED",
        "SUPPRESSION_METADATA_INVALID",
    }


def _synthetic_finding(*, maturity: str = "experimental") -> Finding:
    return Finding(
        rule_id="TEST/EXPERIMENTAL",
        severity=Severity.WARNING,
        tier="static",
        maturity=maturity,  # type: ignore[arg-type]
        title="Experimental check",
        file="agent.py",
        line=1,
        fingerprint="experimental-fingerprint",
        evidence=[Evidence(kind="test", detail="test")],
        verdict=Verdict(observed="Observed", implies="Risk", recommended="Fix", tradeoff="Cost"),
        citations=[Citation(publisher="Test", title="Test", url="https://example.com")],
        excerpt="x = 1",
        remediation=Remediation(complexity="trivial"),
    )


def test_experimental_marking_all_reporters_and_fail_on_opt_in(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    report = Report(
        scan_root=str(tmp_path),
        coverage=Coverage(experimental_rules_evaluated=["TEST/EXPERIMENTAL"]),
        findings=[_synthetic_finding()],
    )
    assert "EXPERIMENTAL" in render_terminal(report)
    assert "experimental" in render_html(report)
    assert "experimental" in render_github(report)
    assert '"maturity": "experimental"' in render_sarif(report)
    monkeypatch.setattr("uptocode.cli.scan_path", lambda *args, **kwargs: report)
    target = tmp_path / "agent.py"
    target.write_text("x = 1\n", encoding="utf-8")
    runner = CliRunner()
    default = runner.invoke(app, ["scan", str(target), "--fail-on", "warning"])
    included = runner.invoke(
        app,
        ["scan", str(target), "--fail-on", "warning", "--include-experimental"],
    )
    assert default.exit_code == 0
    assert included.exit_code == 1


def test_share_safe_scrubs_all_absolute_path_forms() -> None:
    root = r"C:\Users\private\deep\repo"
    report = Report(
        scan_root=root,
        findings=[_synthetic_finding(maturity="stable")],
        analysis_warnings=[
            AnalysisWarning(
                code="PATH",
                message=(
                    root
                    + r" C:\secret\file.py \\server\share\file.py"
                    + " /home/alice/repo/file.py /Users/bob/repo/file.py"
                ),
            )
        ],
    )
    safe = make_share_safe(report)
    rendered = "\n".join(
        [safe.model_dump_json(), render_html(safe), render_sarif(safe)]
    )
    assert safe.scan_root == "<scan-root>"
    for sentinel in (root, r"C:\secret", r"\\server\share", "/home/", "/Users/"):
        assert sentinel not in rendered


def test_pre_commit_hook_badges_and_version_contract() -> None:
    root = Path(__file__).parents[1]
    hooks = yaml.safe_load((root / ".pre-commit-hooks.yaml").read_text(encoding="utf-8"))
    hook = hooks[0]
    assert hook["id"] == "uptocode"
    assert hook["language"] == "python"
    assert hook["entry"] == "uptocode scan . --fail-on critical"
    assert hook["pass_filenames"] is False
    assert hook["always_run"] is True
    readme = (root / "README.md").read_text(encoding="utf-8")
    assert "img.shields.io/pypi/v/uptocode.svg" in readme
    assert "scanned%20with-UpToCode" in readme
