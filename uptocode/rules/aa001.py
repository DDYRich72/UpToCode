"""AA001: unbounded agent loop."""

from __future__ import annotations

from uptocode.adapters.python import LoopEvidence
from uptocode.fingerprints import finding_fingerprint
from uptocode.models import (
    AnalysisWarning,
    Evidence,
    Finding,
    FindingContext,
    Remediation,
    Severity,
    Verdict,
)
from uptocode.rules.registry import core_rule_map


def evaluate_aa001(
    loop: LoopEvidence,
    *,
    file: str,
    excerpt: str,
) -> tuple[Finding | None, AnalysisWarning | None]:
    definition = core_rule_map()["AA001"]
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
        maturity=definition.maturity,
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
            recommended=(
                "Terminate on the framework's semantic completion signal (final output, "
                "LangGraph END, or Anthropic end_turn rather than tool_use); also enforce "
                "a hard turn or budget ceiling and preserve partial results at that ceiling."
            ),
            tradeoff="A cap can truncate legitimately long tasks.",
        ),
        citations=[citation.to_public() for citation in definition.citations],
        excerpt=excerpt,
        context=FindingContext(framework=loop.framework),
        remediation=Remediation(complexity="moderate"),
    )
    return finding, None
