# Validation Report

Phase 1 exact-commit fresh-clone environments: Windows Python 3.13.7 / Node 22.19.0
and Ubuntu/WSL Python 3.13.12 / Node 22.22.2. The configured GitHub matrix targets
Python 3.11–3.13 on Ubuntu, Windows, and macOS; workflow burn-in continues in Phase 3.

## Reference production gates

| Gate | Status | Evidence |
|---|---|---|
| Python suite | PASS | Fresh clones on Windows and Ubuntu/WSL: `python -m pytest -q` → 158 passed, including official-client hosted HTTP lifecycle |
| Offline product acceptance | PASS | Fresh clones on both platforms: real installed-process stdio MCP, malformed-call recovery, CLI/report/review/plan/non-mutation, clean/bad fixtures |
| Production dogfood | PASS | Fresh clones on both platforms: zero production findings, zero suppressions, zero analysis warnings; `.archagent-audit/architecture-compliance.json` |
| Ruff | PASS | Fresh clones on both platforms: all checks passed |
| Strict typing | PASS | Fresh clones on both platforms: no issues in 29 source files |
| Branch coverage | PASS | Fresh clones on both platforms: 86%, exceeding the configured 85% release floor |
| Wheel | PASS | `archagent_audit-1.0.0-py3-none-any.whl` built, installed in an isolated environment, imported from site-packages, and exercised through stdio MCP |
| Python dependency audit | PASS | Fresh Windows isolated install with upgraded pip: `pip check` reports no broken requirements and `pip-audit --local --skip-editable` reports no known vulnerabilities |
| Report 2.0 | PASS | strict contracts, stable fingerprints, rule states, metadata/usage, baselines, SARIF, and Report 1.0 clean-reader compatibility tests |
| Analyzer hardening | PASS | unified-diff context reconstruction, strict Draft 2020-12 schemas, project evidence resolution, pruned nested ignores, unsupported-state warnings, and `super().__init__` false-positive regression |
| CLI | PASS | module/version execution, file/directory scans, baselines, changed-since, selectors, excludes, severity overrides, GitHub/SARIF, timing, and warning gates |
| Local MCP | PASS | official SDK stdio lifecycle; full typed tool catalog, malformed-call survival, workspace containment, workspace diff bases, progress, and explicit judgment consent |
| Hosted MCP | PASS | official SDK Streamable HTTP lifecycle; bearer authorization, four-request transport concurrency probe, health/readiness, no path tools, submitted-source limits, output cap, and no-persistence test |
| Judgment boundary | PASS (mocked) | Structured Outputs, trusted metadata merge, redaction, bounded calls/tokens/retries/timeouts, consent, refusal/failure preservation, and prompt-injection cases |
| Packaging/release | PASS (artifact level) | non-root Dockerfile, Cloud Run limits/secrets/probes, protected release environment, SBOM and provenance attestation workflow, operations/rollback runbook |
| Functional site | PASS | Fresh Windows and Ubuntu/WSL clones build `/` and `/connect`; both server-rendered route tests pass. The required Sites Vite plugin is now tracked outside ignored build output. |
| Site dependency audit | PASS AT RELEASE THRESHOLD / REVIEW REQUIRED | Fresh `npm audit --omit=dev --audit-level=high` exits 0 and reports two moderate findings in Next's nested PostCSS; Phase 4 must upgrade or record accepted risk. |
| Container build | PASS IN FIRST CI / SMOKE PENDING | GitHub run `29691320624` built the container successfully; the Phase 3 health/401 smoke is not yet implemented. |

## Safety and external actions

- Static analysis makes no network calls and submitted-source temporary directories are removed after each request.
- Source, prompts, keys, email addresses, and SSNs are absent from captured judgment failure logs; hosted operational logs are payload-free by policy and implementation.
- Review and FIXPLAN generation do not modify scanned repositories.
- No package publication, site deployment, Cloud Run deployment, public repository
  release, submission, or new paid model request was performed.
- The historical single authorized synthetic GPT-5.6 smoke remains recorded in `.archagent-audit/live-smoke.json`; a post-build/post-deploy smoke requires fresh explicit approval.

## Phase 1 submission-ready evidence

- Demo commands for terminal, HTML, JSON, review, manifest-bound FIXPLAN, and
  compliance all completed from exact commit `846c7f7` in the fresh Windows clone.
  The critical scan returned
  the expected exit code 1; all artifact-producing commands returned 0.
- The checked-in evidence under `docs/submission-evidence/` contains only synthetic
  fixtures and sanitized paths. The sanitized report and review manifest regenerate
  the approved-only FIXPLAN successfully.
- Fresh Windows and Ubuntu/WSL clones each passed 158 tests, acceptance, compliance,
  Ruff, strict mypy over 29 files, 86% branch coverage, clean npm installation,
  production site build, and two rendered-route tests.
- The Windows npm install emitted one non-fatal cleanup warning for an optional nested
  WASM directory; it exited 0, and the build and rendered-route tests passed. The Ubuntu
  install was clean.
- Phase 0 is remotely preserved as `v1.0.0-rc1`. The Phase 1 commit and evidence update
  remain local; pushing and creating/pushing `v1.0.0-rc2` require operator approval.
- The operator must capture the Codex Session ID outside the repository before submission.
- GitHub Actions is not yet claimed green. The first burn-in run failed only in the
  site job (now-fixed ignored plugin) and Python 3.11 dependency-audit environment;
  workflow isolation is explicit Phase 3 work.

Release and submission remain approval-gated per Completion Plan v2. PyPI naming,
publication, and MCP registry submission are post-event Phase 7 work.
