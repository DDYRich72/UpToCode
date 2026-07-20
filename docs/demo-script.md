# UpToCode Demo Script — Under Three Minutes

Target runtime: **2:50–2:55**, including pauses. Narration audio is required.

## Beat 1 — 0:00–0:18 — Problem and position

“Agent code can be syntactically valid and still ship with an unbounded loop, no budget,
an ungated destructive tool, or no eval coverage. UpToCode is a Python-first
architecture-quality scanner. It uses deterministic evidence first, optional GPT-5.6
judgment second, and never auto-rewrites the repository.”

Show only the UpToCode README and the `scan → review → plan` flow.

## Beat 2 — 0:18–0:48 — Bad fixture and coverage-aware report

Run `uptocode scan fixtures/bad_python --fail-on critical`, then open the prepared
standalone HTML report. Show AA001, AA003, the redacted AA006 excerpt, analyzed-file
coverage, judgment status, citations, and the absence of a fabricated quality score.

## Beat 3 — 0:48–1:08 — Deterministic and judgment evidence

Explain that an omitted OpenAI Agents SDK `max_turns` is bounded by the SDK default,
whereas explicit `max_turns=None` is a static finding. Show the prepared, redacted GPT-5.6
Structured Outputs result for a contextual candidate. State that judgment is double opt-in,
bounded, redacted, uses `store=false`, and cannot erase static findings. Do not make a live
paid request during recording.

## Beat 4 — 1:08–1:38 — Review and plan without mutation

Run:

```text
uptocode review report.json --approve AA001,AA003 --reject AA012 --non-interactive
uptocode plan report.json --manifest .uptocode/manifest.json --output FIXPLAN.md
```

Show the report fingerprint binding, approved-only findings, evidence, ordered steps,
acceptance checks, risks, and copy-paste Codex prompt. Show that the fixture is unchanged.

## Beat 5 — 1:38–2:03 — MCP guardrail

Show a coding agent calling `check_loop` with `while True:\n    work()` and receiving AA001
before code is written. Name the ten-tool local surface:
`audit_source`, `audit_file`, `audit_repo`, `audit_diff`, `check_tool_schema`, `check_loop`,
`list_rules`, `get_rule`, `review_findings`, and `generate_fixplan`. Hosted mode exposes
only submitted-content tools—never repository or filesystem-path tools. Its bearer-key
boundary applies an in-memory per-key limit, defaults hosted judgment off, and logs only a
short credential-digest prefix. Local file, repository, and diff-base tools remain contained
to the canonical root resolved when the server starts.
State that the submitted pre-production endpoint passed readiness, unauthorized access,
AA001, judgment-gate, rate-limit, and payload-free-log checks with zero paid model calls;
do not claim a production UpToCode endpoint until the Phase 7 migration is verified.

## Beat 6 — 2:03–2:28 — Delivery surfaces and self-audit

Show SARIF, injection-safe GitHub annotations, the bounded job summary, the composite
Action's upload-before-fail sequence, baselines, changed-since scanning, and rule selection
from prepared outputs or help text. Run `python scripts/compliance.py`; show the zero-finding
production self-scan and the offline acceptance PASS evidence. Say, “UpToCode audits
itself: zero production findings, suppressions, or unexplained warnings.” Show the selected
rc6 verification run `29717587213`—do not imply that the composite Action
itself publishes a package or deploys a service.

## Codex/GPT-5.6 development beat and close — 2:28–2:55

“Codex collaborated throughout: turning the specification into vertical slices, building
the scanner, reports, MCP, site, and tests, fixing clean-clone defects, and enforcing the
Windows and Linux gates. GPT-5.6 powers the explicitly consented Structured Outputs
judgment tier. UpToCode completes that loop by turning cited findings and human approvals
into a Codex-ready FIXPLAN—before production and before source mutation.”

Show the “Built with Codex and GPT-5.6” README section and the validation matrix.

## Recording guardrails

- Final exported video must be **less than 3:00** and include clear narration audio.
- Use only UpToCode-owned UI, checked-in fixtures, generated redacted reports, and plain
  terminal/browser chrome; show no third-party logos, trademarks, copyrighted clips, or
  music.
- Do not display API keys, environment values, private source outside this repository,
  account identifiers, the Codex Session ID, or hidden browser content.
- Record or upload nothing until the applicable operator approval is explicit.
- Keep claims aligned with the shipped surface: Python 1.0; no TypeScript analysis,
  source-changing auto-fix, PR comment bot, package publication, or public service.
