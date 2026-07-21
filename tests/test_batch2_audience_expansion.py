from __future__ import annotations

from datetime import datetime, timezone
from html import unescape
import json
from pathlib import Path
import re

import pytest
from typer.testing import CliRunner

from uptocode.cli import app
from uptocode.engine import TYPESCRIPT_STATIC_RULES, scan_path
from uptocode.mcp_server import audit_diff, audit_source
from uptocode.models import Report, ReviewDecision, ReviewManifest
from uptocode.reporters.github import render_github_summary
from uptocode.reporters.html import render_html
from uptocode.reporters.terminal import render_terminal
from uptocode.review import report_fingerprint


ROOT = Path(__file__).parents[1]


def test_batch2_fingerprints_match_deliberate_golden() -> None:
    expected = json.loads((ROOT / "tests" / "golden" / "batch2_fingerprints.json").read_text())
    actual = {
        fixture: [
            finding.fingerprint
            for finding in scan_path(ROOT / "fixtures" / fixture).findings
        ]
        for fixture in expected
    }
    assert actual == expected


@pytest.mark.parametrize(
    ("bad_fixture", "clean_fixture", "framework"),
    [
        ("bad_anthropic", "clean_anthropic", "anthropic"),
        ("bad_crewai", "clean_crewai", "crewai"),
        ("bad_pydantic_ai", "clean_pydantic_ai", "pydantic-ai"),
        ("bad_llamaindex", "clean_llamaindex", "llamaindex"),
        ("bad_ts", "clean_ts", "openai-agents-js"),
    ],
)
def test_framework_fixtures_are_positive_and_clean(
    bad_fixture: str, clean_fixture: str, framework: str
) -> None:
    bad = scan_path(ROOT / "fixtures" / bad_fixture)
    clean = scan_path(ROOT / "fixtures" / clean_fixture)

    assert bad.findings
    assert framework in bad.coverage.frameworks_detected
    assert clean.findings == []
    assert framework in clean.coverage.frameworks_detected


def test_anthropic_protocol_loop_is_clean_and_text_cap_is_flagged(tmp_path: Path) -> None:
    (tmp_path / "agent.py").write_text(
        """import anthropic
client = anthropic.Anthropic(timeout=10, max_retries=2)
budget = 4
response = client.messages.create(model='x', max_tokens=10, messages=[])
while response.stop_reason == 'tool_use':
    if budget <= 0:
        break
    response = client.messages.create(model='x', max_tokens=10, messages=[])
""",
        encoding="utf-8",
    )
    report = scan_path(tmp_path)
    assert not [finding for finding in report.findings if finding.rule_id == "AA001"]

    (tmp_path / "agent.py").write_text(
        """import anthropic
client = anthropic.Anthropic()
response = client.messages.create(model='x', messages=[])
turns = 0
while turns < 3:
    turns += 1
    if 'DONE' in str(response.content):
        break
    response = client.messages.create(model='x', messages=[])
""",
        encoding="utf-8",
    )
    report = scan_path(tmp_path)
    assert [finding for finding in report.findings if finding.rule_id == "AA001"]


def test_adapter_suppression_unsupported_and_false_positive_contract(tmp_path: Path) -> None:
    (tmp_path / "agent.py").write_text(
        """from llama_index.core.agent.workflow import AgentWorkflow
class DynamicWorkflow(AgentWorkflow):
    pass
""",
        encoding="utf-8",
    )
    unsupported = scan_path(tmp_path)
    assert "UNSUPPORTED_LLAMAINDEX_WORKFLOW" in {
        warning.code for warning in unsupported.analysis_warnings
    }

    (tmp_path / "agent.py").write_text(
        """import anthropic
client = anthropic.Anthropic()
response = client.messages.create(model='x', messages=[])
while True:  # uptocode: ignore AA001
    response = client.messages.create(model='x', messages=[])
""",
        encoding="utf-8",
    )
    suppressed = scan_path(tmp_path)
    assert not [finding for finding in suppressed.findings if finding.rule_id == "AA001"]

    (tmp_path / "agent.py").write_text("import anthropic\nprint('documentation only')\n", encoding="utf-8")
    false_positive = scan_path(tmp_path)
    assert false_positive.findings == []


def test_typescript_report_22_coverage_and_mixed_repository(tmp_path: Path) -> None:
    (tmp_path / "agent.ts").write_text(
        "import { run } from '@openai/agents';\nwhile (true) { run(agent, {}); }\n",
        encoding="utf-8",
    )
    (tmp_path / "plain.py").write_text("print('ok')\n", encoding="utf-8")
    report = scan_path(tmp_path)

    assert report.schema_version == "2.2"
    by_language = {item.language: item for item in report.coverage.language_coverage}
    assert set(by_language) == {"python", "typescript"}
    assert set(by_language["typescript"].rules_evaluated) == TYPESCRIPT_STATIC_RULES
    assert "AA003" in by_language["typescript"].rules_not_applicable
    assert report.coverage.files_analyzed == 2
    assert "Language Typescript" in render_terminal(report)
    assert "Typescript" in render_github_summary(report)


def test_typescript_extensions_parse_recovery_and_suppression(tmp_path: Path) -> None:
    (tmp_path / "component.tsx").write_text(
        "export const View = () => <div>{value}</div>;\nwhile (true) { work(); } // uptocode: ignore AA001\n",
        encoding="utf-8",
    )
    (tmp_path / "module.mts").write_text("while (true) {\n", encoding="utf-8")
    report = scan_path(tmp_path)

    assert report.coverage.files_discovered == 2
    assert "TYPESCRIPT_PARSE_RECOVERY" in {warning.code for warning in report.analysis_warnings}
    assert not [
        finding
        for finding in report.findings
        if finding.rule_id == "AA001" and finding.file == "component.tsx"
    ]


def test_mcp_accepts_typescript_source_and_diff() -> None:
    source_report = audit_source(
        "while (true) { work(); }", filename="agent.ts"
    )
    diff_report = audit_diff(
        "--- /dev/null\n+++ b/agent.ts\n@@ -0,0 +1,1 @@\n+while (true) { work(); }\n"
    )

    assert source_report.findings[0].file == "agent.ts"
    assert diff_report.findings[0].file == "agent.ts"


def test_html_review_data_is_bound_safe_and_manifest_compatible(tmp_path: Path) -> None:
    hostile = "</script><script>globalThis.owned=true</script>&"
    (tmp_path / "agent.ts").write_text(
        f"while (true) {{ work({hostile!r}); }}\n", encoding="utf-8"
    )
    report = scan_path(tmp_path)
    report.findings[0].title = hostile
    rendered = render_html(report)

    assert "script-src 'unsafe-inline'" in rendered
    assert "fetch(" not in rendered
    assert "XMLHttpRequest" not in rendered
    assert "</script><script>globalThis.owned=true</script>" not in rendered
    assert "\\u003c/script\\u003e" in rendered
    assert 'aria-live="polite"' in rendered
    assert 'aria-pressed="false"' in rendered
    assert "uptocode-review-manifest.json" in rendered

    match = re.search(
        r'<script id="uptocode-review-data" type="application/json">(.*?)</script>',
        rendered,
        re.DOTALL,
    )
    assert match is not None
    embedded = json.loads(unescape(match.group(1)))
    assert embedded["report_fingerprint"] == report_fingerprint(report)
    decision = ReviewDecision(
        fingerprint=embedded["findings"][0]["fingerprint"], status="approved"
    )
    manifest = ReviewManifest(
        schema_version="2.0",
        report_fingerprint=embedded["report_fingerprint"],
        created_at=datetime.now(timezone.utc),
        decisions=[decision],
    )
    assert list(manifest.model_dump(mode="json")) == [
        "schema_version",
        "report_fingerprint",
        "created_at",
        "decisions",
    ]


def test_report_22_round_trip_is_strict() -> None:
    report = scan_path(ROOT / "fixtures" / "clean_ts")
    assert Report.model_validate_json(report.model_dump_json()) == report


def test_cli_html_and_json_outputs_share_one_report_fingerprint(tmp_path: Path) -> None:
    (tmp_path / "agent.ts").write_text("while (true) { work(); }\n", encoding="utf-8")
    html_path = tmp_path / "report.html"
    json_path = tmp_path / "report.json"

    result = CliRunner().invoke(
        app,
        [
            "scan",
            str(tmp_path),
            "--format",
            "html",
            "--output",
            str(html_path),
            "--json-output",
            str(json_path),
        ],
    )

    assert result.exit_code == 0, result.output
    report = Report.model_validate_json(json_path.read_text(encoding="utf-8"))
    assert report_fingerprint(report) in html_path.read_text(encoding="utf-8")
