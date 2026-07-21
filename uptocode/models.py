"""Versioned public contracts shared by every UpToCode surface."""

from __future__ import annotations

from datetime import date, datetime, timezone
from enum import StrEnum
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from uptocode import __version__


class StrictModel(BaseModel):
    """Reject unknown public fields so boundary drift fails closed."""

    model_config = ConfigDict(extra="forbid")


class Severity(StrEnum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


SEVERITY_ORDER = {
    Severity.CRITICAL: 0,
    Severity.WARNING: 1,
    Severity.INFO: 2,
}


class Evidence(StrictModel):
    kind: str
    detail: str


class Verdict(StrictModel):
    observed: str
    implies: str
    recommended: str
    tradeoff: str


class Citation(StrictModel):
    publisher: str = Field(validation_alias=AliasChoices("publisher", "vendor"))
    title: str
    url: str
    status: Literal["normative", "supporting"] = "normative"


class Remediation(StrictModel):
    complexity: Literal["trivial", "moderate", "complex"]
    status: Literal["proposed", "approved", "rejected", "planned"] = "proposed"
    plan: str | None = None


class FindingContext(StrictModel):
    framework: str | None = None
    candidate_rule: str | None = None


class Finding(StrictModel):
    rule_id: str
    severity: Severity
    tier: Literal["static", "judgment"]
    maturity: Literal["stable", "experimental"] = "stable"
    title: str
    file: str
    line: int = Field(ge=1)
    fingerprint: str
    evidence: list[Evidence]
    verdict: Verdict
    citations: list[Citation]
    excerpt: str
    context: FindingContext = Field(default_factory=FindingContext)
    remediation: Remediation


class AnalysisWarning(StrictModel):
    code: str
    message: str
    file: str | None = None
    line: int | None = None


class SkippedFile(StrictModel):
    path: str
    reason: str


RuleStatus = Literal[
    "passed",
    "finding",
    "suppressed",
    "inconclusive",
    "unsupported",
    "not_applicable",
    "not_requested",
    "failed",
]


class RuleResult(StrictModel):
    rule_id: str
    status: RuleStatus
    finding_count: int = 0
    detail: str | None = None


class Coverage(StrictModel):
    files_discovered: int = 0
    files_analyzed: int = 0
    files_skipped: int = 0
    frameworks_detected: list[str] = Field(default_factory=list)
    rules_evaluated: list[str] = Field(default_factory=list)
    experimental_rules_evaluated: list[str] = Field(default_factory=list)
    rules_not_applicable: list[str] = Field(default_factory=list)
    skipped_files: list[SkippedFile] = Field(default_factory=list)
    baseline_findings: int = 0
    baseline_new: int = 0
    baseline_resolved: int = 0
    language_coverage: list["LanguageCoverage"] = Field(default_factory=list)


class LanguageCoverage(StrictModel):
    language: Literal["python", "typescript"]
    files_discovered: int = 0
    files_analyzed: int = 0
    rules_evaluated: list[str] = Field(default_factory=list)
    experimental_rules_evaluated: list[str] = Field(default_factory=list)
    rules_not_applicable: list[str] = Field(default_factory=list)


class SuppressionDetail(StrictModel):
    file: str
    line: int = Field(ge=1)
    rule: str
    owner: str | None = None
    reason: str | None = None
    expires: date | None = None


class BaselineDebtItem(StrictModel):
    fingerprint: str
    rule_id: str
    file: str
    first_seen: datetime
    age_days: int = Field(default=0, ge=0)


class BaselineDebt(StrictModel):
    new: list[BaselineDebtItem] = Field(default_factory=list)
    aging: list[BaselineDebtItem] = Field(default_factory=list)
    resolved: list[BaselineDebtItem] = Field(default_factory=list)


class ScanMetadata(StrictModel):
    duration_ms: int = Field(default=0, ge=0)
    repository_revision: str | None = None
    configuration_fingerprint: str
    rulepack_fingerprint: str


class JudgmentUsage(StrictModel):
    model: str | None = None
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    requests: int = Field(default=0, ge=0)


class RedactionCounts(StrictModel):
    secrets: int = 0
    pii: int = 0

    def add(self, other: "RedactionCounts") -> None:
        self.secrets += other.secrets
        self.pii += other.pii


class Report(StrictModel):
    schema_version: str = "2.2"
    tool_version: str = __version__
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
    suppression_details: list[SuppressionDetail] = Field(default_factory=list)
    baseline_debt: BaselineDebt = Field(default_factory=BaselineDebt)
    rule_results: list[RuleResult] = Field(default_factory=list)
    metadata: ScanMetadata | None = None
    judgment_usage: JudgmentUsage = Field(default_factory=JudgmentUsage)


class ReviewDecision(StrictModel):
    fingerprint: str
    status: Literal["approved", "rejected"]
    note: str | None = None


class ReviewManifest(StrictModel):
    schema_version: str = "2.0"
    report_fingerprint: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    decisions: list[ReviewDecision]


class FixResult(StrictModel):
    rule_id: str
    fingerprint: str
    file: str
    branch: str
    worktree: str
    runner_exit: int | None = None
    fingerprint_gone: bool | None = None
    verification_status: Literal["not_requested", "not_run", "passed", "failed"]
    verification_exit: int | None = None
    status: Literal["PASS", "FAIL"]
    reason: str | None = None


class FixSession(StrictModel):
    schema_version: str = "1.0"
    report_fingerprint: str
    base_revision: str
    results: list[FixResult] = Field(default_factory=list)
