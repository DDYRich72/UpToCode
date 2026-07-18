# Validation Report

Environment: Python 3.13.7 on Windows; project supports Python 3.11+.

Resolved direct environment: pydantic 2.13.4, typer 0.27.0, rich 14.3.4, PyYAML 6.0.3, pathspec 0.12.1, openai 2.46.0, mcp 1.28.1, pytest 9.1.1.

| Criterion | Status | Evidence |
|---|---|---|
| Gate 1 scaffold and AA001 | PASS | `python -m pytest -q` → 13 passed; AA001 matrix, deterministic report, redaction, discovery, and exit-code tests included |
| Gate 2 Python static engine | NOT RUN | — |
| Full offline suite | PASS (Gate 1) | `python -m pytest -q` → 13 passed |
| Bad/clean fixtures | NOT RUN | — |
| Secret redaction | NOT RUN | — |
| Judgment failure matrix | NOT RUN | — |
| Review and planning non-mutation | NOT RUN | — |
| Standalone HTML visual inspection | NOT RUN | — |
| MCP integration | NOT RUN | — |
| Self-scan triage | NOT RUN | — |
| Cross-platform acceptance | NOT RUN | — |
| Authorized GPT-5.6 live smoke | BLOCKED — APPROVAL | API key and paid-use approval required |
| README/demo claims | NOT RUN | — |
