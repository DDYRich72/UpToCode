# Validation Report

Environment: Python 3.13.7 on Windows; project supports Python 3.11+.

Resolved direct environment: pydantic 2.13.4, typer 0.27.0, rich 14.3.4, PyYAML 6.0.3, pathspec 0.12.1, openai 2.46.0, mcp 1.28.1, pytest 9.1.1.

| Criterion | Status | Evidence |
|---|---|---|
| Gate 1 scaffold and AA001 | PASS | `python -m pytest -q` → 13 passed; AA001 matrix, deterministic report, redaction, discovery, and exit-code tests included |
| Gate 2 Python static engine | PASS | `python -m pytest -q` → 49 passed; static rules, edge matrices, candidate extraction, registry, terminal, coverage, and error behavior included |
| Gate 3 developer surfaces | PASS | `python -m pytest -q` → 71 passed; mocked structured judgment, review/plan, standalone HTML, and five MCP tools included |
| Full offline suite | PASS (Gate 3) | `python -m pytest -q` → 71 passed |
| Bad/clean fixtures | PASS | Bad fixture matches deliberate fingerprint golden; clean fixture has zero findings/warnings |
| Secret redaction | PASS (static surfaces) | Raw sentinel absent from JSON and terminal assertions; environment secret flow cases pass |
| Judgment failure matrix | PASS (mocked) | Structured success, refusal, timeout, unavailable authentication, partial failure, bounded/redacted payload, and static preservation pass |
| Review and planning non-mutation | PASS | Temporary repository tests verify report fingerprinting, manifest decisions, deterministic FIXPLAN, and unchanged source files |
| Standalone HTML structure | PASS | Inline-only HTML, CSP, semantic sections, fixed bar chart, escaped excerpts, redaction, and CLI output behavior pass |
| Standalone HTML visual inspection | DEFERRED | In-app browser rejected local `file://` navigation under security policy; manual/local served inspection remains in Gate 4 |
| MCP integration | PASS | Five tools exposed; static default and consent boundary pass; AA001 detected through `check_loop` and `audit_diff`; malformed call followed by valid call passes |
| Self-scan triage | NOT RUN | — |
| Cross-platform acceptance | NOT RUN | — |
| Authorized GPT-5.6 live smoke | BLOCKED — APPROVAL | API key and paid-use approval required |
| README/demo claims | NOT RUN | — |
