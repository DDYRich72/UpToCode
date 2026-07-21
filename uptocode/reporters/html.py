"""Standalone HTML reporting with local, report-bound review decisions."""

from __future__ import annotations

from collections import Counter
from html import escape
import json

from uptocode.models import Report, Severity
from uptocode.review import report_fingerprint


def _text(value: object) -> str:
    return escape(str(value), quote=True)


def _script_json(value: object) -> str:
    """Serialize untrusted data without allowing an HTML script-block breakout."""
    return (
        json.dumps(value, ensure_ascii=True, separators=(",", ":"))
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
    )


def render_html(report: Report) -> str:
    """Render a portable local report with an offline review-manifest download."""
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
    review_findings: list[dict[str, object]] = []
    for finding in report.findings:
        maturity_badge = (
            '<span class="badge">experimental</span> '
            if finding.maturity == "experimental"
            else ""
        )
        citations = "".join(
            f'<li><a href="{_text(citation.url)}">{_text(citation.title)}</a> '
            f'<span class="muted">({_text(citation.publisher)} · {_text(citation.status)})</span></li>'
            for citation in finding.citations
        )
        evidence = "".join(
            f"<li><strong>{_text(item.kind)}:</strong> {_text(item.detail)}</li>"
            for item in finding.evidence
        )
        fingerprint = _text(finding.fingerprint)
        finding_cards.append(
            f'<article class="finding {finding.severity.value}" data-finding="{fingerprint}">'
            f'<header><span class="badge">{_text(finding.severity.value)}</span> '
            f'{maturity_badge}'
            f'<strong>{_text(finding.rule_id)} · {_text(finding.title)}</strong></header>'
            f'<p class="location">{_text(finding.file)}:{finding.line}</p>'
            f'<div class="decision-controls" role="group" aria-label="Review {_text(finding.rule_id)}">'
            f'<button type="button" data-decision="approved" data-fingerprint="{fingerprint}" aria-pressed="false">Approve</button>'
            f'<button type="button" data-decision="rejected" data-fingerprint="{fingerprint}" aria-pressed="false">Reject</button>'
            f'</div>'
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
        review_findings.append(
            {
                "fingerprint": finding.fingerprint,
                "rule_id": finding.rule_id,
                "title": finding.title,
                "file": finding.file,
                "line": finding.line,
            }
        )
    warnings = "".join(
        f"<li><strong>{_text(warning.code)}</strong> — {_text(warning.message)}</li>"
        for warning in report.analysis_warnings
    ) or "<li>None</li>"
    frameworks = ", ".join(report.coverage.frameworks_detected) or "None detected"
    language_rows = "".join(
        f"<tr><th>{_text(item.language.title())}</th>"
        f"<td>{item.files_analyzed}/{item.files_discovered}</td>"
        f"<td>{_text(', '.join(item.rules_evaluated + item.experimental_rules_evaluated) or 'None')}</td>"
        f"<td>{_text(', '.join(item.rules_not_applicable) or 'None')}</td></tr>"
        for item in report.coverage.language_coverage
    ) or '<tr><td colspan="4">No supported languages discovered.</td></tr>'
    review_data = _script_json(
        {
            "report_fingerprint": report_fingerprint(report),
            "findings": review_findings,
        }
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src data:">
<title>UpToCode architecture report</title>
<style>
:root{{--ink:#17202a;--muted:#667085;--line:#d0d5dd;--paper:#fff;--wash:#f7f8fa;--critical:#b42318;--warning:#b54708;--info:#175cd3;--approved:#067647;--rejected:#b42318}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--wash);color:var(--ink);font:15px/1.55 system-ui,sans-serif}}
main{{max-width:980px;margin:auto;padding:40px 22px 80px}} h1{{font-size:2rem;margin:.15rem 0}} h2{{margin-top:2rem}}
.eyebrow,.muted,.location{{color:var(--muted)}} .summary{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px}}
.metric,.panel,.finding{{background:var(--paper);border:1px solid var(--line);border-radius:10px;padding:18px}}
.metric strong{{display:block;font-size:1.55rem}} .bar-row{{display:grid;grid-template-columns:80px 1fr 30px;gap:12px;align-items:center;margin:10px 0}}
.bar-track{{height:12px;background:#eaecf0;border-radius:6px;overflow:hidden}} .bar{{display:block;height:100%;min-width:0}}
.bar.critical{{background:var(--critical)}} .bar.warning{{background:var(--warning)}} .bar.info{{background:var(--info)}}
.finding{{margin:14px 0;border-left-width:5px}} .finding.critical{{border-left-color:var(--critical)}} .finding.warning{{border-left-color:var(--warning)}} .finding.info{{border-left-color:var(--info)}}
.badge{{border:1px solid currentColor;border-radius:999px;padding:2px 8px;text-transform:uppercase;font-size:.72rem}} pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#101828;color:#f2f4f7;padding:12px;border-radius:7px}} a{{color:#175cd3}} details{{margin-top:12px}}
.review-bar{{position:sticky;top:0;z-index:2;display:flex;gap:14px;align-items:center;justify-content:space-between;margin:20px 0;padding:14px 18px;background:#fff;border:1px solid var(--line);border-radius:10px;box-shadow:0 4px 14px #10182814}}
button{{font:inherit;border:1px solid var(--line);border-radius:7px;background:#fff;padding:7px 12px;cursor:pointer}} button:disabled{{cursor:not-allowed;opacity:.55}}
button:focus-visible,a:focus-visible{{outline:3px solid #84adff;outline-offset:2px}}
button[data-decision="approved"][aria-pressed="true"]{{color:#fff;background:var(--approved);border-color:var(--approved)}} button[data-decision="rejected"][aria-pressed="true"]{{color:#fff;background:var(--rejected);border-color:var(--rejected)}}
.decision-controls{{display:flex;gap:8px;margin:12px 0}} table{{width:100%;border-collapse:collapse}} th,td{{border-bottom:1px solid var(--line);padding:8px;text-align:left;vertical-align:top}}
@media (max-width:620px){{.review-bar{{align-items:stretch;flex-direction:column}} .bar-row{{grid-template-columns:65px 1fr 24px}}}}
</style></head><body><main>
<p class="eyebrow">Static architecture-quality analysis</p><h1>UpToCode architecture report</h1>
<p>{_text(report.scan_root)} · Judgment: {_text(report.judgment_status)}</p>
<section class="summary" aria-label="Report summary">
<div class="metric"><strong>{len(report.findings)}</strong>Findings</div>
<div class="metric"><strong>{report.coverage.files_analyzed}/{report.coverage.files_discovered}</strong>Files analyzed</div>
<div class="metric"><strong>{len(report.analysis_warnings)}</strong>Analysis warnings</div>
<div class="metric"><strong>{report.redactions.secrets + report.redactions.pii}</strong>Sensitive values redacted</div></section>
<section class="review-bar" aria-label="Review decisions"><strong id="decision-counter" aria-live="polite">0 of {len(report.findings)} findings decided</strong><button type="button" id="download-manifest" disabled>Download review manifest</button></section>
<section class="panel"><h2>Findings by category</h2>{bars}</section>
<section class="panel"><h2>Coverage</h2><p>Frameworks: {_text(frameworks)}</p>
<p>Rules evaluated: {_text(', '.join(report.coverage.rules_evaluated) or 'None')}</p>
<p>Experimental rules evaluated: {_text(', '.join(report.coverage.experimental_rules_evaluated) or 'None')}</p>
<table><thead><tr><th>Language</th><th>Files</th><th>Rules evaluated</th><th>Not applicable</th></tr></thead><tbody>{language_rows}</tbody></table>
<p>Baseline debt: {len(report.baseline_debt.new)} new · {len(report.baseline_debt.aging)} aging · {len(report.baseline_debt.resolved)} resolved</p>
<h3>Analysis warnings</h3><ul>{warnings}</ul></section>
<section><h2>Findings</h2>{''.join(finding_cards) or '<p>No findings at the configured threshold.</p>'}</section>
<script id="uptocode-review-data" type="application/json">{review_data}</script>
<script>
(() => {{
  'use strict';
  const review = JSON.parse(document.getElementById('uptocode-review-data').textContent);
  const decisions = new Map();
  const counter = document.getElementById('decision-counter');
  const download = document.getElementById('download-manifest');
  const refresh = () => {{
    counter.textContent = `${{decisions.size}} of ${{review.findings.length}} findings decided`;
    download.disabled = decisions.size === 0;
  }};
  document.querySelectorAll('[data-decision]').forEach((button) => {{
    button.addEventListener('click', () => {{
      const fingerprint = button.dataset.fingerprint;
      const status = button.dataset.decision;
      const active = button.getAttribute('aria-pressed') === 'true';
      document.querySelectorAll(`[data-fingerprint="${{fingerprint}}"]`).forEach((peer) => peer.setAttribute('aria-pressed', 'false'));
      if (active) decisions.delete(fingerprint);
      else {{ decisions.set(fingerprint, status); button.setAttribute('aria-pressed', 'true'); }}
      refresh();
    }});
  }});
  download.addEventListener('click', () => {{
    const manifest = {{
      schema_version: '2.0',
      report_fingerprint: review.report_fingerprint,
      created_at: new Date().toISOString(),
      decisions: review.findings
        .filter((finding) => decisions.has(finding.fingerprint))
        .map((finding) => ({{ fingerprint: finding.fingerprint, status: decisions.get(finding.fingerprint) }})),
    }};
    const blob = new Blob([JSON.stringify(manifest, null, 2) + '\\n'], {{type: 'application/json'}});
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'uptocode-review-manifest.json';
    anchor.click();
    URL.revokeObjectURL(url);
  }});
  refresh();
}})();
</script>
</main></body></html>"""
