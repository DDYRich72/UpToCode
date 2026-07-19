# ArchAgent Demo Script — Under Three Minutes

## 0:00–0:25 — Problem and position

“Agent code can be syntactically valid and still ship with an unbounded loop, no budget, an ungated destructive tool, or no eval coverage. ArchAgent is a Python-first architecture-quality scanner. It uses deterministic evidence first, optional GPT‑5.6 judgment second, and never auto-rewrites the repository.”

Show the README positioning and the `scan → review → plan` flow.

## 0:25–1:05 — Bad fixture and coverage-aware report

Run:

```text
archagent-audit scan fixtures/bad_python --fail-on critical
archagent-audit scan fixtures/bad_python --format html --output report.html
```

Show AA001 at the unbounded loop, AA003 at the destructive tool, and the redacted API key. Open `report.html`; point out files analyzed, judgment status, redaction count, findings bar chart, direct citations, and the absence of a fabricated quality score.

## 1:05–1:35 — Deterministic and judgment evidence

Explain that omitted `Runner.run(max_turns=...)` is clean because the SDK supplies a bounded default, while explicit `max_turns=None` is a static finding. Then show one pre-authorized GPT‑5.6 judgment result for a tool-schema candidate. State that only redacted, bounded excerpts were sent and that static findings survive refusal or API failure.

Do not run the live request during recording unless cost and code-sharing approval have already been recorded.

## 1:35–2:10 — Review and plan, without source mutation

Run:

```text
archagent-audit scan fixtures/bad_python --format json --output report.json
archagent-audit review report.json --approve AA001,AA003 --reject AA012 --non-interactive
archagent-audit plan report.json --manifest .archagent-audit/manifest.json --output FIXPLAN.md
```

Open `FIXPLAN.md`. Show the objective, evidence, likely files, ordered steps, acceptance checks, risks, and copy-paste Codex prompt. Emphasize that the fixture and git worktree remain unchanged.

## 2:10–2:35 — MCP guardrail

Show a coding agent calling:

```json
{"tool":"check_loop","arguments":{"snippet":"while True:\n    work()"}}
```

Show AA001 before code is written. Name the complete ten-tool local surface:
`audit_source`, `audit_file`, `audit_repo`, `audit_diff`, `check_tool_schema`,
`check_loop`, `list_rules`, `get_rule`, `review_findings`, and `generate_fixplan`.
Hosted mode deliberately exposes only the submitted-content subset and no path tools.

## 2:35–2:55 — Evidence and close

Run `python scripts/acceptance.py` and show the passing suite, real stdio MCP probe, self-scan path, and unchanged worktree assertion.

Close: “ArchAgent turns architecture concerns into cited evidence, explicit approvals, and a Codex-ready plan—before production and before source mutation.”

## Recording guardrails

- Do not display API keys, environment values, private code, account identifiers, or hidden browser content.
- Use only checked-in fixtures and generated redacted reports.
- Record or upload nothing until the applicable operator approval is explicit.
- Keep claims aligned with README limitations: Python MVP; no TypeScript analysis,
  composite GitHub Action, auto-fix, PR comment, or public service.
