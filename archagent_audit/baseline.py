"""Stable finding baselines for brownfield CI adoption."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import Field

from archagent_audit.models import Finding, Report, StrictModel


class Baseline(StrictModel):
    schema_version: str = "2.0"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    fingerprints: list[str]


def create_baseline(report: Report) -> Baseline:
    if report.schema_version != "2.0":
        raise ValueError("Only Report 2.0 can create a baseline")
    return Baseline(fingerprints=sorted({item.fingerprint for item in report.findings}))


def apply_baseline(report: Report, baseline: Baseline) -> tuple[Report, list[Finding]]:
    if report.schema_version != baseline.schema_version:
        raise ValueError("Baseline and report schema versions do not match")
    known = set(baseline.fingerprints)
    existing = [item for item in report.findings if item.fingerprint in known]
    report.findings = [item for item in report.findings if item.fingerprint not in known]
    report.coverage.baseline_findings = len(existing)
    return report, existing
