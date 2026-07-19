"""SARIF 2.1.0 rendering for code-scanning consumers."""

from __future__ import annotations

import json

from archagent_audit.models import Report, Severity


_LEVEL = {Severity.CRITICAL: "error", Severity.WARNING: "warning", Severity.INFO: "note"}


def render_sarif(report: Report) -> str:
    rules: dict[str, dict[str, object]] = {}
    results: list[dict[str, object]] = []
    for finding in report.findings:
        citation = finding.citations[0] if finding.citations else None
        rule: dict[str, object] = {
            "id": finding.rule_id,
            "name": finding.title,
            "shortDescription": {"text": finding.title},
            "defaultConfiguration": {"level": _LEVEL[finding.severity]},
        }
        if citation is not None:
            rule["helpUri"] = citation.url
        rules.setdefault(
            finding.rule_id,
            rule,
        )
        results.append(
            {
                "ruleId": finding.rule_id,
                "level": _LEVEL[finding.severity],
                "message": {"text": finding.verdict.observed},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": finding.file},
                            "region": {"startLine": finding.line},
                        }
                    }
                ],
                "partialFingerprints": {"archagentFinding": finding.fingerprint},
            }
        )
    payload = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "ArchAgent",
                        "version": report.tool_version,
                        "rules": [rules[key] for key in sorted(rules)],
                    }
                },
                "results": results,
            }
        ],
    }
    return json.dumps(payload, indent=2)
