"""Optional GPT-5.6 judgment tier using Responses structured parsing."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import Literal

from pydantic import BaseModel

from archagent_audit.judgment_candidates import JudgmentCandidate
from archagent_audit.models import (
    AnalysisWarning,
    Citation,
    Evidence,
    Finding,
    Remediation,
    Report,
    SEVERITY_ORDER,
    Severity,
    Verdict,
)
from archagent_audit.redaction import redact_text
from archagent_audit.rules.registry import load_core_rules


class JudgmentFinding(BaseModel):
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


class JudgmentBatch(BaseModel):
    findings: list[JudgmentFinding]


def _warning(rule_id: str, code: str, message: str) -> AnalysisWarning:
    return AnalysisWarning(
        code=code,
        message=message,
        file=None,
        line=None,
    )


def _error_code(error: BaseException) -> tuple[str, str]:
    name = type(error).__name__.lower()
    if isinstance(error, TimeoutError) or "timeout" in name:
        return "JUDGMENT_TIMEOUT", "Judgment timed out; static results were preserved."
    if "authentication" in name or "permission" in name:
        return (
            "JUDGMENT_AUTHENTICATION_FAILED",
            "Judgment authentication failed; static results were preserved.",
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


def _fingerprint(item: JudgmentFinding) -> str:
    raw = f"{item.rule_id}|{item.file}|{item.line}|judgment".encode()
    return hashlib.sha256(raw).hexdigest()[:16]


def _to_finding(
    item: JudgmentFinding,
    candidate: JudgmentCandidate,
    allowed_urls: list[str],
) -> Finding:
    citation_url = item.citation_url if item.citation_url in allowed_urls else allowed_urls[0]
    return Finding(
        rule_id=item.rule_id,
        severity=Severity(item.severity),
        tier="judgment",
        title=item.title,
        file=item.file,
        line=item.line,
        fingerprint=_fingerprint(item),
        evidence=[Evidence(kind="architectural-judgment", detail=candidate.evidence)],
        verdict=Verdict(
            observed=item.observed,
            implies=item.implies,
            recommended=item.recommended,
            tradeoff=item.tradeoff,
        ),
        citations=[Citation(vendor="Primary guidance", title="Rule guidance", url=citation_url)],
        excerpt=redact_text(candidate.excerpt)[0],
        context={"candidate_rule": candidate.rule_id},
        remediation=Remediation(complexity="complex"),
    )


def run_judgment(
    report: Report,
    candidates: list[JudgmentCandidate],
    *,
    client: object,
) -> Report:
    """Run one structured Responses call per rule and merge valid findings."""
    if not candidates:
        report.judgment_status = "completed"
        return report
    definitions = {definition.id: definition for definition in load_core_rules()}
    grouped: dict[str, list[JudgmentCandidate]] = defaultdict(list)
    for candidate in candidates:
        grouped[candidate.rule_id].append(candidate)
    failures = 0
    successes = 0
    for rule_id in sorted(grouped):
        rule_candidates = grouped[rule_id]
        payload = _candidate_payload(rule_candidates, report)
        try:
            response = client.responses.parse(
                model="gpt-5.6",
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
        except BaseException as error:
            code, message = _error_code(error)
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
        allowed_urls = [str(url).rstrip("/") for url in definitions[rule_id].citations]
        by_location = {(item.file, item.line): item for item in rule_candidates}
        for item in parsed.findings:
            candidate = by_location.get((item.file, item.line))
            if candidate is None or item.rule_id != rule_id:
                continue
            duplicate = any(
                finding.rule_id == item.rule_id
                and finding.file == item.file
                and finding.line == item.line
                for finding in report.findings
            )
            if not duplicate:
                report.findings.append(_to_finding(item, candidate, allowed_urls))
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

