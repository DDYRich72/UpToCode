"""Stable finding baselines and debt lifecycle tracking."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import Field

from uptocode.models import BaselineDebt, BaselineDebtItem, Finding, Report, StrictModel


class BaselineEntry(StrictModel):
    fingerprint: str
    rule_id: str
    file: str
    first_seen: datetime


class Baseline(StrictModel):
    schema_version: Literal["2.1"] = "2.1"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    entries: list[BaselineEntry]


class LegacyBaseline(StrictModel):
    schema_version: Literal["2.0"] = "2.0"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    fingerprints: list[str]


def load_baseline(content: str) -> Baseline:
    try:
        return Baseline.model_validate_json(content)
    except ValueError:
        legacy = LegacyBaseline.model_validate_json(content)
        return Baseline(
            created_at=legacy.created_at,
            entries=[
                BaselineEntry(
                    fingerprint=fingerprint,
                    rule_id="unknown",
                    file="unknown",
                    first_seen=legacy.created_at,
                )
                for fingerprint in sorted(set(legacy.fingerprints))
            ],
        )


def create_baseline(
    report: Report,
    *,
    previous: Baseline | None = None,
    findings: list[Finding] | None = None,
    now: datetime | None = None,
) -> Baseline:
    if report.schema_version not in {"2.0", "2.1"}:
        raise ValueError("Only Report 2.0 or 2.1 can create a baseline")
    timestamp = now or datetime.now(timezone.utc)
    previous_by_fingerprint = {
        entry.fingerprint: entry for entry in (previous.entries if previous else [])
    }
    entries = []
    for finding in sorted(findings if findings is not None else report.findings, key=lambda item: item.fingerprint):
        prior = previous_by_fingerprint.get(finding.fingerprint)
        entries.append(
            BaselineEntry(
                fingerprint=finding.fingerprint,
                rule_id=finding.rule_id,
                file=finding.file,
                first_seen=prior.first_seen if prior else timestamp,
            )
        )
    unique = {entry.fingerprint: entry for entry in entries}
    return Baseline(created_at=timestamp, entries=[unique[key] for key in sorted(unique)])


def _debt_item(entry: BaselineEntry, now: datetime) -> BaselineDebtItem:
    first_seen = entry.first_seen
    if first_seen.tzinfo is None:
        first_seen = first_seen.replace(tzinfo=timezone.utc)
    return BaselineDebtItem(
        fingerprint=entry.fingerprint,
        rule_id=entry.rule_id,
        file=entry.file,
        first_seen=first_seen,
        age_days=max(0, (now.date() - first_seen.astimezone(timezone.utc).date()).days),
    )


def apply_baseline(
    report: Report,
    baseline: Baseline,
    *,
    findings: list[Finding] | None = None,
    now: datetime | None = None,
    mute: bool = True,
) -> tuple[Report, list[Finding]]:
    if report.schema_version not in {"2.0", "2.1"}:
        raise ValueError("Baseline requires a Report 2.x document")
    timestamp = now or datetime.now(timezone.utc)
    scanned = list(findings if findings is not None else report.findings)
    scanned_by_fingerprint = {item.fingerprint: item for item in scanned}
    baseline_by_fingerprint = {item.fingerprint: item for item in baseline.entries}
    existing = [item for item in scanned if item.fingerprint in baseline_by_fingerprint]
    new_entries = [
        BaselineEntry(
            fingerprint=item.fingerprint,
            rule_id=item.rule_id,
            file=item.file,
            first_seen=timestamp,
        )
        for item in scanned
        if item.fingerprint not in baseline_by_fingerprint
    ]
    aging_entries = [
        baseline_by_fingerprint[item.fingerprint] for item in existing
    ]
    resolved_entries = [
        item for item in baseline.entries if item.fingerprint not in scanned_by_fingerprint
    ]
    report.coverage.baseline_findings = len(aging_entries)
    report.coverage.baseline_new = len(new_entries)
    report.coverage.baseline_resolved = len(resolved_entries)
    report.baseline_debt = BaselineDebt(
        new=[_debt_item(item, timestamp) for item in new_entries],
        aging=[_debt_item(item, timestamp) for item in aging_entries],
        resolved=[_debt_item(item, timestamp) for item in resolved_entries],
    )
    if mute:
        known = set(baseline_by_fingerprint)
        report.findings = [item for item in report.findings if item.fingerprint not in known]
    return report, existing
