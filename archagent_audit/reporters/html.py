"""Standalone, dependency-free HTML reporting."""

from __future__ import annotations

from collections import Counter
from html import escape

from archagent_audit.models import Report, Severity


def _text(value: object) -> str:
    return escape(str(value), quote=True)


def render_html(report: Report) -> str:
    """Render a portable report with no external assets or executable scripts."""
    counts = Counter(finding.severity.value for finding in report.findings)
    maximum = max(counts.values(), default=1)
    bars = "".join(
        f'<div class="bar-row"><span>{severity.value.title()}</span>'
        f'<div class="bar-track"><span class="bar {severity.value}" '
        f'style="width:{(counts[severity.value] / maximum) * 100:.1f}%"></span></div>'
        f'<strong>{counts[severity.value]}</strong></div>'
        for severity in Severity
    )
    finding_cards = []
    for finding in report.findings:
        citations = "".join(
            f'<li><a href="{_text(citation.url)}">{_text(citation.title)}</a> '
            f'<span class="muted">({_text(citation.vendor)})</span></li>'
            for citation in finding.citations
        )
        evidence = "".join(
            f"<li><strong>{_text(item.kind)}:</strong> {_text(item.detail)}</li>"
            for item in finding.evidence
        )
        finding_cards.append(
            f'<article class="finding {finding.severity.value}">'
            f'<header><span class="badge">{_text(finding.severity.value)}</span> '
            f'<strong>{_text(finding.rule_id)} · {_text(finding.title)}</strong></header>'
            f'<p class="location">{_text(finding.file)}:{finding.line}</p>'
            f'<pre>{_text(finding.excerpt)}</pre>'
            f'<h3>Evidence</h3><ul>{evidence}</ul>'
            f'<p><strong>Observed:</strong> {_text(finding.verdict.observed)}</p>'
            f'<p><strong>Why it matters:</strong> {_text(finding.verdict.implies)}</p>'
            f'<p><strong>Recommended:</strong> {_text(finding.verdict.recommended)}</p>'
            f'<p><strong>Tradeoff:</strong> {_text(finding.verdict.tradeoff)}</p>'
            f'<p><strong>Remediation complexity:</strong> {_text(finding.remediation.complexity)}</p>'
            f'<details><summary>Primary references</summary><ul>{citations}</ul></details>'
            "</article>"
        )
    warnings = "".join(
        f"<li><strong>{_text(warning.code)}</strong> — {_text(warning.message)}</li>"
        for warning in report.analysis_warnings
    ) or "<li>None</li>"
    frameworks = ", ".join(report.coverage.frameworks_detected) or "None detected"
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:">
<title>ArchAgent architecture report</title>
<style>
:root{{--ink:#17202a;--muted:#667085;--line:#d0d5dd;--paper:#fff;--wash:#f7f8fa;--critical:#b42318;--warning:#b54708;--info:#175cd3}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--wash);color:var(--ink);font:15px/1.55 system-ui,sans-serif}}
main{{max-width:980px;margin:auto;padding:40px 22px 80px}} h1{{font-size:2rem;margin:.15rem 0}} h2{{margin-top:2rem}}
.eyebrow,.muted,.location{{color:var(--muted)}} .summary{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px}}
.metric,.panel,.finding{{background:var(--paper);border:1px solid var(--line);border-radius:10px;padding:18px}}
.metric strong{{display:block;font-size:1.55rem}} .bar-row{{display:grid;grid-template-columns:80px 1fr 30px;gap:12px;align-items:center;margin:10px 0}}
.bar-track{{height:12px;background:#eaecf0;border-radius:6px;overflow:hidden}} .bar{{display:block;height:100%;min-width:0}}
.bar.critical{{background:var(--critical)}} .bar.warning{{background:var(--warning)}} .bar.info{{background:var(--info)}}
.finding{{margin:14px 0;border-left-width:5px}} .finding.critical{{border-left-color:var(--critical)}} .finding.warning{{border-left-color:var(--warning)}} .finding.info{{border-left-color:var(--info)}}
.badge{{border:1px solid currentColor;border-radius:999px;padding:2px 8px;text-transform:uppercase;font-size:.72rem}} pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#101828;color:#f2f4f7;padding:12px;border-radius:7px}} a{{color:#175cd3}} details{{margin-top:12px}}
</style></head><body><main>
<p class="eyebrow">Static architecture-quality analysis</p><h1>ArchAgent architecture report</h1>
<p>{_text(report.scan_root)} · Judgment: {_text(report.judgment_status)}</p>
<section class="summary" aria-label="Report summary">
<div class="metric"><strong>{len(report.findings)}</strong>Findings</div>
<div class="metric"><strong>{report.coverage.files_analyzed}/{report.coverage.files_discovered}</strong>Files analyzed</div>
<div class="metric"><strong>{len(report.analysis_warnings)}</strong>Analysis warnings</div>
<div class="metric"><strong>{report.redactions.secrets + report.redactions.pii}</strong>Sensitive values redacted</div></section>
<section class="panel"><h2>Findings by category</h2>{bars}</section>
<section class="panel"><h2>Coverage</h2><p>Frameworks: {_text(frameworks)}</p>
<p>Rules evaluated: {_text(', '.join(report.coverage.rules_evaluated) or 'None')}</p>
<h3>Analysis warnings</h3><ul>{warnings}</ul></section>
<section><h2>Findings</h2>{''.join(finding_cards) or '<p>No findings at the configured threshold.</p>'}</section>
</main></body></html>"""
