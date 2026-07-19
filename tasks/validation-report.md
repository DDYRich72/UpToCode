# Validation Report

Phase 2 exact-commit fresh-clone environments: Windows Python 3.13.7 / Node 24.14.1
and Ubuntu/WSL Python 3.13.12 / Node 22.22.2. The configured GitHub matrix targets
Python 3.11–3.13 on Ubuntu, Windows, and macOS; workflow burn-in continues in Phase 3.

## Reference production gates

| Gate | Status | Evidence |
|---|---|---|
| Python suite | PASS | Fresh clones on Windows and Ubuntu/WSL: `python -m pytest -q` → 167 passed, including MCP hardening and official-client hosted HTTP lifecycle |
| Offline product acceptance | PASS | Fresh clones on both platforms: 167 tests, real installed-process stdio MCP, malformed-call recovery, CLI/report/review/plan/non-mutation, clean/bad fixtures |
| Production dogfood | PASS | Fresh clones on both platforms: zero production findings, zero suppressions, zero analysis warnings; `.archagent-audit/architecture-compliance.json` |
| Ruff | PASS | Fresh clones on both platforms: all checks passed |
| Strict typing | PASS | Fresh clones on both platforms: no issues in 29 source files |
| Branch coverage | PASS | Fresh clones on both platforms: 87%, exceeding the configured 85% release floor |
| Wheel | PASS | `archagent_audit-1.0.0-py3-none-any.whl` built, installed in an isolated environment, imported from site-packages, and exercised through stdio MCP |
| Python dependency audit | PASS | Fresh Windows isolated install with upgraded pip: `pip check` reports no broken requirements and `pip-audit --local --skip-editable` reports no known vulnerabilities |
| Report 2.0 | PASS | strict contracts, stable fingerprints, rule states, metadata/usage, baselines, SARIF, and Report 1.0 clean-reader compatibility tests |
| Analyzer hardening | PASS | unified-diff context reconstruction, strict Draft 2020-12 schemas, project evidence resolution, pruned nested ignores, unsupported-state warnings, and `super().__init__` false-positive regression |
| CLI | PASS | module/version execution, file/directory scans, baselines, changed-since, selectors, excludes, severity overrides, GitHub/SARIF, timing, and warning gates |
| Local MCP | PASS | official SDK stdio lifecycle; ten typed tools; server-start canonical-root containment for every path surface; guarded FastMCP 1.28.1 strict-schema shim; malformed-call survival; progress; explicit judgment consent |
| Hosted MCP | PASS | official SDK Streamable HTTP lifecycle; bearer authorization; per-key digest token buckets with monotonic refill, bounded eviction, `429` and `Retry-After`; judgment globally off by default; safe short-digest attribution; health/readiness; no path tools; submitted-source limits; output cap; no persistence |
| Judgment boundary | PASS (mocked) | Structured Outputs, trusted metadata merge, redaction, bounded calls/tokens/retries/timeouts, consent, refusal/failure preservation, and prompt-injection cases |
| Packaging/release | PASS (artifact level) | non-root Dockerfile, Cloud Run limits/secrets/probes, protected release environment, SBOM and provenance attestation workflow, operations/rollback runbook |
| Functional site | PASS | Fresh Windows and Ubuntu/WSL clones build `/` and `/connect`; both server-rendered route tests pass. The required Sites Vite plugin is now tracked outside ignored build output. |
| Site dependency audit | PASS AT RELEASE THRESHOLD / REVIEW REQUIRED | Fresh `npm audit --omit=dev --audit-level=high` exits 0 and reports two moderate findings in Next's nested PostCSS; Phase 4 must upgrade or record accepted risk. |
| Container build | PASS IN FIRST CI / NEW SMOKE BURN-IN PENDING | GitHub run `29691320624` built the container successfully. Phase 3 now defines health 200, unauthenticated MCP 401, and bounded shutdown checks; execution awaits the approved burn-in push. |

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
- Phase 0 and Phase 1 are remotely preserved as `v1.0.0-rc1` and
  `v1.0.0-rc2`; the repository remains private.
- The operator captured the Codex Session IDs outside the repository.
- GitHub Actions is not yet claimed green. The first burn-in run failed only in the
  site job (now-fixed ignored plugin) and Python 3.11 dependency-audit environment;
  workflow isolation is explicit Phase 3 work.

Release and submission remain approval-gated per Completion Plan v2. PyPI naming,
publication, and MCP registry submission are post-event Phase 7 work.

## Phase 2 submission-ready evidence

- Exact implementation commit `0d07f71` was cloned independently on Windows and
  Ubuntu/WSL.
- Both clones passed 167 tests, offline acceptance, compliance, Ruff, strict mypy
  over 29 source files, and 87% branch coverage. The Windows editable environment
  also passed `pip check`; the POSIX gate used an isolated `uv` environment without
  bundling pip, and all required §3 commands passed.
- Windows (Python 3.13.7 / Node 24.14.1) and Ubuntu/WSL (Python 3.13.12 / Node
  22.22.2) each completed a clean `npm ci`, production builds for `/` and
  `/connect`, and two rendered-route tests.
- The SDK canary pins and exercises FastMCP 1.28.1. Malformed private internals
  fail closed and identify the installed SDK version. Compliance independently
  enforces agreement among project metadata, runtime `__version__`, and
  `server.json` at 1.0.0.
- Focused tests verify path containment after working-directory changes, limiter
  refill and eviction, `429`/`Retry-After`, the default-off hosted judgment gate,
  raw/full-key log exclusion, and version synchronization.
- The exact offline demo sequence generated terminal, JSON, standalone HTML,
  review-manifest, approved-only FIXPLAN, and compliance evidence. Its critical
  fixture scan exited 1 as designed; every artifact-producing command exited 0.
- No paid model call, push, tag, remote-access change, deployment, credential
  distribution, publication, video upload, or submission occurred in Phase 2.

## Phase 3 local burn-in candidate

- Phase 2 is remotely preserved as annotated tag `v1.0.0-rc3` at `f409771`; the
  repository remains private.
- Local Python validation passes 175 tests, offline acceptance, production
  compliance, Ruff, strict mypy over 30 source files, and 88% branch coverage.
- The isolated wheel environment upgrades pip, setuptools, and wheel, installs
  `archagent_audit-1.0.0-py3-none-any.whl`, passes `pip check`, and reports no known
  dependency vulnerabilities. The unpublished ArchAgent package itself is
  correctly reported as unavailable for registry audit.
- A source install matching the composite Action's `version: source` path built
  successfully. Its bad-fixture scan generated ten SARIF results, preserved the
  expected threshold exit code 1, emitted no JSON null, and declared rule default
  levels.
- A clean WSL npm install added 508 packages. ESLint, `tsc --noEmit`, the
  production build for `/` and `/connect`, and both rendered-route tests pass.
  The required Cloudflare Worker types are explicit until the ratified Drizzle/D1
  removal in Phase 4.
- Workflow YAML and Action contracts parse under PyYAML and are covered by hostile
  command-data, summary-bound, no-null SARIF, SHA-pin, audit-isolation, Docker-smoke,
  artifact-retention, and upload-before-fail tests.
- Docker and `actionlint` are unavailable on the local Windows host. The first
  fully green GitHub run, nine-cell matrix, Linux container lifecycle, and native
  workflow interpretation therefore remain unverified until an operator-approved
  burn-in push. No green-run claim is made yet.
- PyPI publication was removed from the release-candidate workflow in accordance
  with D006; tagged builds retain and attest artifacts without publishing them.
