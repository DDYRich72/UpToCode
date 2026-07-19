# Validation Report

Environment: Windows, Python 3.13, Node 24. The supported CI matrix is Python 3.11–3.13 on Ubuntu, Windows, and macOS; Node 22 is used for the site gate.

## Reference production gates

| Gate | Status | Evidence |
|---|---|---|
| Python suite | PASS | `python -m pytest -q` → 158 passed, including official-client hosted HTTP lifecycle |
| Offline product acceptance | PASS | `python scripts/acceptance.py` → real installed-process stdio MCP, malformed-call recovery, CLI/report/review/plan/non-mutation, clean/bad fixtures |
| Production dogfood | PASS | `python scripts/compliance.py` → zero production findings, zero suppressions, zero analysis warnings; `.archagent-audit/architecture-compliance.json` |
| Ruff | PASS | `python -m ruff check archagent_audit tests scripts` |
| Strict typing | PASS | `python -m mypy archagent_audit` → no issues in 29 source files |
| Branch coverage | PASS | 86%, exceeding the configured 85% release floor |
| Wheel | PASS | `archagent_audit-1.0.0-py3-none-any.whl` built, installed in an isolated environment, imported from site-packages, and exercised through stdio MCP |
| Python dependency audit | PASS | Clean isolated install with upgraded packaging toolchain and Starlette 1.3.1: `pip check` and `pip-audit` report no broken requirements or known vulnerabilities |
| Report 2.0 | PASS | strict contracts, stable fingerprints, rule states, metadata/usage, baselines, SARIF, and Report 1.0 clean-reader compatibility tests |
| Analyzer hardening | PASS | unified-diff context reconstruction, strict Draft 2020-12 schemas, project evidence resolution, pruned nested ignores, unsupported-state warnings, and `super().__init__` false-positive regression |
| CLI | PASS | module/version execution, file/directory scans, baselines, changed-since, selectors, excludes, severity overrides, GitHub/SARIF, timing, and warning gates |
| Local MCP | PASS | official SDK stdio lifecycle; full typed tool catalog, malformed-call survival, workspace containment, workspace diff bases, progress, and explicit judgment consent |
| Hosted MCP | PASS | official SDK Streamable HTTP lifecycle; bearer authorization, four-request transport concurrency probe, health/readiness, no path tools, submitted-source limits, output cap, and no-persistence test |
| Judgment boundary | PASS (mocked) | Structured Outputs, trusted metadata merge, redaction, bounded calls/tokens/retries/timeouts, consent, refusal/failure preservation, and prompt-injection cases |
| Packaging/release | PASS (artifact level) | non-root Dockerfile, Cloud Run limits/secrets/probes, protected release environment, SBOM and provenance attestation workflow, operations/rollback runbook |
| Functional site | PASS | Vinext production build completed for `/` and `/connect`; both routes pass server-rendered HTML tests, responsive CSS states are present, and live HTTP returned 200. Browser automation CLI was unavailable, so no screenshot evidence was produced. |
| Site dependency audit | PASS AT RELEASE THRESHOLD / REVIEW REQUIRED | `npm audit --omit=dev --audit-level=high` exits 0; it reports two moderate findings in Next's nested PostCSS dependency with no non-breaking automated fix. Security review must disposition these before release. |
| Container build | NOT RUN LOCALLY | Docker is not installed in this environment; `docker build` remains a required CI gate |

## Safety and external actions

- Static analysis makes no network calls and submitted-source temporary directories are removed after each request.
- Source, prompts, keys, email addresses, and SSNs are absent from captured judgment failure logs; hosted operational logs are payload-free by policy and implementation.
- Review and FIXPLAN generation do not modify scanned repositories.
- No package publication, site deployment, Cloud Run deployment, repository publication, submission, or new paid model request was performed.
- The historical single authorized synthetic GPT-5.6 smoke remains recorded in `.archagent-audit/live-smoke.json`; a post-build/post-deploy smoke requires fresh explicit approval.

Release remains approval-gated for package-name review, security review, dependency/SBOM review, judge access, publication, and deployment.
