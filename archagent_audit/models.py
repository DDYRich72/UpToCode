"""Versioned public contracts shared by every ArchAgent surface."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class Severity(StrEnum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


SEVERITY_ORDER = {
    Severity.CRITICAL: 0,
    Severity.WARNING: 1,
    Severity.INFO: 2,
}


class Evidence(BaseModel):
    kind: str
    detail: str


class Verdict(BaseModel):
    observed: str
    implies: str
    recommended: str
    tradeoff: str


class Citation(BaseModel):
    vendor: str
    title: str
    url: str


class Remediation(BaseModel):
    complexity: Literal["trivial", "moderate", "complex"]
    status: Literal["proposed", "approved", "rejected", "planned"] = "proposed"
    plan: str | None = None


class Finding(BaseModel):
    rule_id: str
    severity: Severity
    tier: Literal["static", "judgment"]
    title: str
    file: str
    line: int = Field(ge=1)
    fingerprint: str
    evidence: list[Evidence]
    verdict: Verdict
    citations: list[Citation]
    excerpt: str
    context: dict[str, Any] = Field(default_factory=dict)
    remediation: Remediation


class AnalysisWarning(BaseModel):
    code: str
    message: str
    file: str | None = None
    line: int | None = None


class Coverage(BaseModel):
    files_discovered: int = 0
    files_analyzed: int = 0
    files_skipped: int = 0
    frameworks_detected: list[str] = Field(default_factory=list)
    rules_evaluated: list[str] = Field(default_factory=list)
    rules_not_applicable: list[str] = Field(default_factory=list)


class RedactionCounts(BaseModel):
    secrets: int = 0
    pii: int = 0

    def add(self, other: "RedactionCounts") -> None:
        self.secrets += other.secrets
        self.pii += other.pii


class Report(BaseModel):
    schema_version: str = "1.0"
    tool_version: str = "0.1.0"
    scan_root: str
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    findings: list[Finding] = Field(default_factory=list)
    coverage: Coverage = Field(default_factory=Coverage)
    analysis_warnings: list[AnalysisWarning] = Field(default_factory=list)
    judgment_status: Literal[
        "not-requested", "completed", "partial", "failed"
    ] = "not-requested"
    redactions: RedactionCounts = Field(default_factory=RedactionCounts)
    suppressions: int = 0


class ReviewDecision(BaseModel):
    fingerprint: str
    status: Literal["approved", "rejected"]
    note: str | None = None


class ReviewManifest(BaseModel):
    schema_version: str = "1.0"
    report_fingerprint: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    decisions: list[ReviewDecision]

