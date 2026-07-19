"""AA001: unbounded agent loop."""

from __future__ import annotations

from archagent_audit.adapters.python import LoopEvidence
from archagent_audit.fingerprints import finding_fingerprint
from archagent_audit.models import (
    AnalysisWarning,
    Citation,
    Evidence,
    Finding,
    FindingContext,
    Remediation,
    Severity,
    Verdict,
)


RUNNER_CITATION = Citation(
    vendor="OpenAI",
    title="OpenAI Agents SDK runner reference",
    url="https://openai.github.io/openai-agents-python/ref/run/",
)
PRACTICAL_GUIDE_CITATION = Citation(
    vendor="OpenAI",
    title="A practical guide to building agents",
    url="https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf",
)


def evaluate_aa001(
    loop: LoopEvidence,
    *,
    file: str,
    excerpt: str,
) -> tuple[Finding | None, AnalysisWarning | None]:
    if loop.bound_kind in {"sdk-default", "explicit", "custom"}:
        return None, None
    if loop.bound_kind == "unknown":
        return None, AnalysisWarning(
            code="AA001_INCONCLUSIVE_BOUND",
            message="Could not resolve the configured turn bound.",
            file=file,
            line=loop.line,
        )
    evidence_kind = (
        "explicit-disabled-limit"
        if loop.framework in {"openai-agents", "langgraph"}
        else "custom-loop-no-exit"
    )
    observed = (
        "Runner.run explicitly disables its turn limit."
        if loop.framework in {"openai-agents", "langgraph"}
        else "A custom while-True agent loop has no detectable exit."
    )
    finding = Finding(
        rule_id="AA001",
        severity=Severity.CRITICAL,
        tier="static",
        title="Unbounded agent loop",
        file=file,
        line=loop.line,
        fingerprint=finding_fingerprint(
            "AA001", file, evidence_kind, detail=loop.detail, excerpt=excerpt
        ),
        evidence=[Evidence(kind=evidence_kind, detail=loop.detail)],
        verdict=Verdict(
            observed=observed,
            implies="A failed tool interaction can continue without a turn ceiling.",
            recommended="Set a turn cap and preserve partial results when the cap is reached.",
            tradeoff="A cap can truncate legitimately long tasks.",
        ),
        citations=[RUNNER_CITATION, PRACTICAL_GUIDE_CITATION],
        excerpt=excerpt,
        context=FindingContext(framework=loop.framework),
        remediation=Remediation(complexity="moderate"),
    )
    return finding, None
