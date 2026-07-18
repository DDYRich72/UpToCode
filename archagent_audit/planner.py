"""Generate deterministic, non-mutating Codex remediation plans."""

from __future__ import annotations

from archagent_audit.models import Finding, Report, ReviewManifest
from archagent_audit.review import report_fingerprint


def _entry(finding: Finding) -> str:
    steps = [
        "Inspect the cited location and its callers to confirm the evidence.",
        f"Implement the smallest change that satisfies: {finding.verdict.recommended}",
        "Add a regression test for the observed failure and a clean counterpart.",
        "Run the targeted test and the full project validation suite.",
    ]
    checks = [
        f"ArchAgent no longer emits {finding.rule_id} at this location.",
        "The clean counterpart remains finding-free.",
        "Existing behavior and public contracts remain intact.",
    ]
    prompt = (
        f"Address ArchAgent finding {finding.rule_id} ({finding.fingerprint}) in "
        f"{finding.file}:{finding.line}. Observed: {finding.verdict.observed} "
        f"Required outcome: {finding.verdict.recommended} Preserve existing behavior, "
        "add regression coverage, run the relevant checks, and report evidence."
    )
    return "\n".join(
        [
            f"## {finding.rule_id}: {finding.title}",
            "",
            f"Fingerprint: `{finding.fingerprint}`",
            "",
            "### Objective",
            "",
            finding.verdict.recommended,
            "",
            "### Evidence",
            "",
            f"- Location: `{finding.file}:{finding.line}`",
            f"- {finding.evidence[0].detail}",
            "",
            "### Likely files",
            "",
            f"- `{finding.file}`",
            "",
            "### Implementation steps",
            "",
            *[f"{index}. {step}" for index, step in enumerate(steps, start=1)],
            "",
            "### Acceptance checks",
            "",
            *[f"- [ ] {check}" for check in checks],
            "",
            "### Risks and tradeoffs",
            "",
            finding.verdict.tradeoff,
            "",
            "### Codex prompt",
            "",
            "```text",
            prompt,
            "```",
            "",
        ]
    )


def generate_fixplan(report: Report, manifest: ReviewManifest) -> str:
    if manifest.report_fingerprint != report_fingerprint(report):
        raise ValueError("Review manifest does not match this report")
    approved = {
        decision.fingerprint
        for decision in manifest.decisions
        if decision.status == "approved"
    }
    findings = [finding for finding in report.findings if finding.fingerprint in approved]
    sections = ["# ArchAgent FIXPLAN", "", "Generated from explicitly approved findings.", ""]
    if not findings:
        sections.extend(["No findings were approved.", ""])
    for finding in findings:
        sections.append(_entry(finding))
    return "\n".join(sections)

