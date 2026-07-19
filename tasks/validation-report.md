# Validation Report

Environment: Python 3.13.7 on Windows; project supports Python 3.11+.

Resolved direct environment: pydantic 2.13.4, typer 0.27.0, rich 14.3.4, PyYAML 6.0.3, pathspec 0.12.1, openai 2.46.0, mcp 1.28.1, pytest 9.1.1.

| Criterion | Status | Evidence |
|---|---|---|
| Gate 1 scaffold and AA001 | PASS | `python -m pytest -q` → 13 passed; AA001 matrix, deterministic report, redaction, discovery, and exit-code tests included |
| Gate 2 Python static engine | PASS | `python -m pytest -q` → 49 passed; static rules, edge matrices, candidate extraction, registry, terminal, coverage, and error behavior included |
| Gate 3 developer surfaces | PASS | `python -m pytest -q` → 71 passed; mocked structured judgment, review/plan, standalone HTML, and five MCP tools included |
| Full offline suite | PASS (Gate 4) | `python scripts/acceptance.py` → 133 passed plus all acceptance stages |
| Rule contract matrix | PASS | Every AA001–AA012 rule has positive/clean evidence, location suppression coverage, an unsupported-dynamic warning case, and false-positive regression coverage; all judgment rules use schema-valid mocked outcomes |
| Bad/clean fixtures | PASS | Bad fixture matches deliberate fingerprint golden; clean fixture has zero findings/warnings |
| Secret/PII redaction | PASS | Raw sentinels are absent from terminal, JSON, HTML, judgment payload, logs, and snapshots; narrow email/SSN patterns and secret-derived prompt flows pass |
| Judgment failure matrix | PASS (mocked) | Structured success, refusal, timeout, unavailable authentication, partial failure, bounded/redacted payload, and static preservation pass |
| Review and planning non-mutation | PASS | Temporary repository tests verify report fingerprinting, manifest decisions, deterministic FIXPLAN, and unchanged source files |
| Standalone HTML structure | PASS | Inline-only HTML, CSP, semantic sections, fixed bar chart, escaped excerpts, redaction, and CLI output behavior pass |
| Standalone HTML visual inspection | DEFERRED | In-app browser rejected local `file://` navigation under security policy; manual/local served inspection remains in Gate 4 |
| MCP integration | PASS | Five tools exposed; static default and consent boundary pass; AA001 detected through `check_loop` and `audit_diff`; malformed call followed by valid call passes |
| Self-scan triage | PASS | `.archagent-audit/self-scan.json`; 39/39 project files, 19 expected fixture/test findings, zero production-code findings, zero analysis warnings; detailed classification in `PROGRESS.md` |
| Cross-platform acceptance | PASS | Windows Python 3.13: 133-test acceptance PASS; Ubuntu/WSL Python 3.13: full acceptance PASS and 133 tests; Windows Python 3.11 baseline: 133 tests PASS |
| Authorized GPT-5.6 live smoke | BLOCKED — APPROVAL | API key and paid-use approval required |
| README/demo claims | PASS (offline review) | README documents positioning, install, exact CLI, privacy, rule URLs, MCP, limitations, and output; demo and unpublished Devpost drafts match Python MVP |
| External actions | PASS | No deployment, publication, upload, external message, paid usage, or submission performed |
