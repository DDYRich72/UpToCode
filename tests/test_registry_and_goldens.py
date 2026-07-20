from __future__ import annotations

import json
from pathlib import Path

from uptocode.engine import scan_path
from uptocode.rules.registry import load_core_rules


ROOT = Path(__file__).parents[1]


def test_core_registry_has_twelve_ordered_rules_and_direct_urls() -> None:
    rules = load_core_rules()

    assert [rule.id for rule in rules] == [f"AA{index:03d}" for index in range(1, 13)]
    assert all(rule.citations for rule in rules)
    assert all(str(url).startswith("https://") for rule in rules for url in rule.citations)


def test_bad_fixture_fingerprints_match_deliberate_golden() -> None:
    expected = json.loads(
        (ROOT / "tests" / "golden" / "bad_python_fingerprints.json").read_text(
            encoding="utf-8"
        )
    )

    report = scan_path(ROOT / "fixtures" / "bad_python")

    assert [finding.fingerprint for finding in report.findings] == expected

