"""Optional GPT-5.6 judgment tier using Responses structured parsing."""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from typing import Any, Literal

from openai import (
    APITimeoutError,
    AuthenticationError,
    PermissionDeniedError,
    RateLimitError,
)

from uptocode.config import JudgmentConfig
from uptocode.judgment_candidates import JudgmentCandidate
from uptocode.fingerprints import finding_fingerprint
from uptocode.models import (
    AnalysisWarning,
    Citation,
    Evidence,
    Finding,
    FindingContext,
    Remediation,
    Report,
    SEVERITY_ORDER,
    Severity,
    StrictModel,
    Verdict,
)
from uptocode.redaction import redact_text
from uptocode.rules.registry import load_core_rules


logger = logging.getLogger(__name__)
JUDGMENT_RULE_BUDGET = 6


class JudgmentFinding(StrictModel):
    rule_id: str
    file: str
    line: int
    title: str
    severity: Literal["critical", "warning", "info"]
    observed: str
    implies: str
    recommended: str
    tradeoff: str
    citation_url: str


class JudgmentBatch(StrictModel):
    findings: list[JudgmentFinding]


def _warning(rule_id: str, code: str, message: str) -> AnalysisWarning:
    return AnalysisWarning(
        code=code,
        message=message,
        file=None,
        line=None,
    )


def _error_code(error: BaseException) -> tuple[str, str]:
    if isinstance(error, (TimeoutError, APITimeoutError)):
        return "JUDGMENT_TIMEOUT", "Judgment timed out; static results were preserved."
    if isinstance(error, AuthenticationError) or type(error).__name__ == "AuthenticationError":
        return (
            "JUDGMENT_AUTHENTICATION_FAILED",
            "Judgment authentication failed; static results were preserved.",
        )
    if isinstance(error, PermissionDeniedError):
        return (
            "JUDGMENT_PERMISSION_DENIED",
            "Judgment permission was denied; static results were preserved.",
        )
    if isinstance(error, RateLimitError):
        return (
            "JUDGMENT_RATE_LIMITED",
            "Judgment was rate limited; static results were preserved.",
        )
    return "JUDGMENT_API_ERROR", "Judgment failed; static results were preserved."


def _candidate_payload(candidates: list[JudgmentCandidate], report: Report) -> str:
    items: list[dict[str, object]] = []
    remaining = 8_000
    for candidate in candidates:
        redacted, counts = redact_text(candidate.excerpt)
        report.redactions.add(counts)
        excerpt = redacted[: min(4_000, remaining)]
        remaining -= len(excerpt)
        items.append(
            {
                "rule_id": candidate.rule_id,
                "file": candidate.file,
                "line": candidate.line,
                "evidence": candidate.evidence,
                "excerpt": excerpt,
            }
        )
        if remaining <= 0:
            break
    return json.dumps(items, ensure_ascii=False)


def _to_finding(
    item: JudgmentFinding,
    candidate: JudgmentCandidate,
    allowed_urls: list[str],
    *,
    trusted_severity: Severity,
    trusted_title: str,
) -> Finding:
    citation_url = item.citation_url if item.citation_url in allowed_urls else allowed_urls[0]
    return Finding(
        rule_id=item.rule_id,
        severity=trusted_severity,
        tier="judgment",
        title=trusted_title,
        file=item.file,
        line=item.line,
        fingerprint=finding_fingerprint(
            item.rule_id,
            item.file,
            "architectural-judgment",
            detail=candidate.evidence,
            excerpt=candidate.excerpt,
        ),
        evidence=[Evidence(kind="architectural-judgment", detail=candidate.evidence)],
        verdict=Verdict(
            observed=item.observed,
            implies=item.implies,
            recommended=item.recommended,
            tradeoff=item.tradeoff,
        ),
        citations=[Citation(vendor="Primary guidance", title="Rule guidance", url=citation_url)],
        excerpt=redact_text(candidate.excerpt)[0],
        context=FindingContext(candidate_rule=candidate.rule_id),
        remediation=Remediation(complexity="complex"),
    )


def run_judgment(
    report: Report,
    candidates: list[JudgmentCandidate],
    *,
    client: object,
    config: JudgmentConfig | None = None,
) -> Report:
    """Run one structured Responses call per rule and merge valid findings."""
    config = config or JudgmentConfig()
    if not candidates:
        report.judgment_status = "completed"
        return report
    definitions = {definition.id: definition for definition in load_core_rules()}
    grouped: dict[str, list[JudgmentCandidate]] = defaultdict(list)
    for candidate in candidates:
        grouped[candidate.rule_id].append(candidate)
    if len(grouped) > config.rule_call_budget:
        report.analysis_warnings.append(
            _warning(
                "*",
                "JUDGMENT_BUDGET_EXCEEDED",
                "Judgment rule-call budget was exceeded; static results were preserved.",
            )
        )
        report.judgment_status = "failed"
        return report
    failures = 0
    successes = 0
    for rule_id in sorted(grouped):
        rule_candidates = grouped[rule_id]
        payload = _candidate_payload(rule_candidates, report)
        report.judgment_usage.model = config.model
        report.judgment_usage.requests += 1
        try:
            request_client: Any = (
                client.with_options(
                    max_retries=config.max_retries,
                    timeout=config.timeout_seconds,
                )
                if hasattr(client, "with_options")
                else client
            )
            response = request_client.responses.parse(
                model=config.model,
                max_output_tokens=config.max_output_tokens,
                timeout=config.timeout_seconds,
                store=False,
                metadata={"component": "uptocode-judgment", "rule_id": rule_id},
                input=[
                    {
                        "role": "system",
                        "content": (
                            "You are an agent-systems architect. Evaluate only the supplied "
                            "rule candidates. Return findings only when the evidence supports "
                            "the rule. Use observed, implies, recommended, and tradeoff reasoning."
                        ),
                    },
                    {"role": "user", "content": payload},
                ],
                text_format=JudgmentBatch,
            )
        except Exception as error:
            code, message = _error_code(error)
            logger.warning("Judgment rule %s failed with %s", rule_id, code)
            report.analysis_warnings.append(_warning(rule_id, code, message))
            failures += 1
            continue
        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            report.analysis_warnings.append(
                _warning(
                    rule_id,
                    "JUDGMENT_REFUSED",
                    "Judgment returned no structured result; static results were preserved.",
                )
            )
            failures += 1
            continue
        successes += 1
        usage = getattr(response, "usage", None)
        report.judgment_usage.input_tokens += int(
            getattr(usage, "input_tokens", 0) or 0
        )
        report.judgment_usage.output_tokens += int(
            getattr(usage, "output_tokens", 0) or 0
        )
        allowed_urls = [str(url).rstrip("/") for url in definitions[rule_id].citations]
        by_location = {(item.file, item.line): item for item in rule_candidates}
        for item in parsed.findings:
            matched_candidate = by_location.get((item.file, item.line))
            if matched_candidate is None or item.rule_id != rule_id:
                continue
            duplicate = any(
                finding.rule_id == item.rule_id
                and finding.file == item.file
                and finding.line == item.line
                for finding in report.findings
            )
            if not duplicate:
                definition = definitions[rule_id]
                report.findings.append(
                    _to_finding(
                        item,
                        matched_candidate,
                        allowed_urls,
                        trusted_severity=definition.severity,
                        trusted_title=definition.name.replace("-", " ").title(),
                    )
                )
    report.judgment_status = (
        "completed" if failures == 0 else "partial" if successes else "failed"
    )
    report.findings.sort(
        key=lambda item: (
            SEVERITY_ORDER[item.severity],
            item.file,
            item.line,
            item.rule_id,
        )
    )
    report.analysis_warnings.sort(
        key=lambda item: (item.file or "", item.line or 0, item.code)
    )
    return report
