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
    matched_approve: set[str] = set()
    matched_reject: set[str] = set()
    decisions: list[ReviewDecision] = []
    for finding in report.findings:
        is_approved = _selected(finding.fingerprint, finding.rule_id, approve)
        is_rejected = _selected(finding.fingerprint, finding.rule_id, reject)
        if is_approved:
            matched_approve.update(
                item for item in approve if item in {finding.fingerprint, finding.rule_id}
            )
        if is_rejected:
            matched_reject.update(
                item for item in reject if item in {finding.fingerprint, finding.rule_id}
            )
        if is_approved and is_rejected:
            raise ValueError(
                f"Finding {finding.fingerprint} is selected for both approval and rejection"
            )
        if is_rejected:
            status = "rejected"
        elif approve_all or is_approved:
            status = "approved"
        else:
            continue
        decisions.append(
            ReviewDecision(fingerprint=finding.fingerprint, status=status)
        )
    unknown = sorted((approve - matched_approve) | (reject - matched_reject))
    if unknown:
        raise ValueError(f"Unknown finding selectors: {', '.join(unknown)}")
    return ReviewManifest(
        report_fingerprint=report_fingerprint(report),
        decisions=decisions,
    )
