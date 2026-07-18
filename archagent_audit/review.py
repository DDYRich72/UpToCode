"""Approval and rejection manifests for immutable scan reports."""

from __future__ import annotations

import hashlib
import json

from archagent_audit.models import Report, ReviewDecision, ReviewManifest


def report_fingerprint(report: Report) -> str:
    payload = report.model_dump(mode="json", exclude={"generated_at"})
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _selected(fingerprint: str, rule_id: str, selectors: set[str]) -> bool:
    return fingerprint in selectors or rule_id in selectors


def create_manifest(
    report: Report,
    *,
    approve: set[str] | None = None,
    reject: set[str] | None = None,
    approve_all: bool = False,
) -> ReviewManifest:
    approve = approve or set()
    reject = reject or set()
    decisions: list[ReviewDecision] = []
    for finding in report.findings:
        if approve_all or _selected(finding.fingerprint, finding.rule_id, approve):
            status = "approved"
        elif _selected(finding.fingerprint, finding.rule_id, reject):
            status = "rejected"
        else:
            continue
        decisions.append(
            ReviewDecision(fingerprint=finding.fingerprint, status=status)
        )
    return ReviewManifest(
        report_fingerprint=report_fingerprint(report),
        decisions=decisions,
    )

