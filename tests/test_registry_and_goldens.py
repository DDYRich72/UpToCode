from __future__ import annotations

import json
from pathlib import Path

from uptocode.engine import scan_path
from uptocode.rules.registry import load_core_rules


ROOT = Path(__file__).parents[1]


def test_core_registry_has_eighteen_ordered_rules_and_structured_citations() -> None:
    rules = load_core_rules()

    assert [rule.id for rule in rules] == [f"AA{index:03d}" for index in range(1, 19)]
    assert all(rule.citations for rule in rules)
    assert all(str(citation.url).startswith("https://") for rule in rules for citation in rule.citations)
    assert all(citation.publisher and citation.title for rule in rules for citation in rule.citations)


def test_bad_fixture_fingerprints_match_deliberate_golden() -> None:
    expected = json.loads(
        (ROOT / "tests" / "golden" / "bad_python_fingerprints.json").read_text(
            encoding="utf-8"
        )
    )

    report = scan_path(ROOT / "fixtures" / "bad_python")

    assert [finding.fingerprint for finding in report.findings] == expected
