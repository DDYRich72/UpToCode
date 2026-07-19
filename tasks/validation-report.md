# Validation Report

Phase 3 implementation commit `790ef5d` passed the complete GitHub matrix in run
`29703827878`: Python 3.11–3.13 on Ubuntu, Windows, and macOS plus package/site,
isolated wheel audit, and container lifecycle jobs. Final exact-candidate Windows
and Ubuntu/WSL clean-clone evidence is recorded below.

## Reference production gates

| Gate | Status | Evidence |
|---|---|---|
| Python suite | PASS | GitHub's nine Python/OS cells: `python -m pytest -q` → 175 passed in every cell; final clean-clone results below |
| Offline product acceptance | PASS | All nine GitHub cells: 175 tests, real installed-process stdio MCP, malformed-call recovery, CLI/report/review/plan/non-mutation, clean/bad fixtures |
| Production dogfood | PASS | Fresh clones on both platforms: zero production findings, zero suppressions, zero analysis warnings; `.archagent-audit/architecture-compliance.json` |
| Ruff | PASS | Fresh clones on both platforms: all checks passed |
| Strict typing | PASS | All nine GitHub cells: no issues in 30 source files |
| Branch coverage | PASS | All nine GitHub cells: 88%, exceeding the configured 85% release floor |
| Wheel | PASS | `archagent_audit-1.0.0-py3-none-any.whl` built, installed in an isolated environment, imported from site-packages, and exercised through stdio MCP |
| Python dependency audit | PASS | Fresh Windows isolated install with upgraded pip: `pip check` reports no broken requirements and `pip-audit --local --skip-editable` reports no known vulnerabilities |
| Report 2.0 | PASS | strict contracts, stable fingerprints, rule states, metadata/usage, baselines, SARIF, and Report 1.0 clean-reader compatibility tests |
| Analyzer hardening | PASS | unified-diff context reconstruction, strict Draft 2020-12 schemas, project evidence resolution, pruned nested ignores, unsupported-state warnings, and `super().__init__` false-positive regression |
| CLI | PASS | module/version execution, file/directory scans, baselines, changed-since, selectors, excludes, severity overrides, GitHub/SARIF, timing, and warning gates |
| Local MCP | PASS | official SDK stdio lifecycle; ten typed tools; server-start canonical-root containment for every path surface; guarded FastMCP 1.28.1 strict-schema shim; malformed-call survival; progress; explicit judgment consent |
| Hosted MCP | PASS | official SDK Streamable HTTP lifecycle; bearer authorization; per-key digest token buckets with monotonic refill, bounded eviction, `429` and `Retry-After`; judgment globally off by default; safe short-digest attribution; health/readiness; no path tools; submitted-source limits; output cap; no persistence |
| Judgment boundary | PASS (mocked) | Structured Outputs, trusted metadata merge, redaction, bounded calls/tokens/retries/timeouts, consent, refusal/failure preservation, and prompt-injection cases |
| Packaging/release | PASS (artifact level) | non-root Dockerfile, Cloud Run limits/secrets/probes, protected release environment, retained wheel/distributions/SBOMs/compliance evidence, public-repository provenance workflow, operations/rollback runbook; private-repository attestation is deferred to Phase 7 |
| Functional site | PASS | Fresh Windows and Ubuntu/WSL clones build `/` and `/connect`; both server-rendered route tests pass. The required Sites Vite plugin is now tracked outside ignored build output. |
| Site dependency audit | PASS AT RELEASE THRESHOLD / REVIEW REQUIRED | Fresh `npm audit --omit=dev --audit-level=high` exits 0 and reports two moderate findings in Next's nested PostCSS; Phase 4 must upgrade or record accepted risk. |
| Container lifecycle | PASS | GitHub run `29703827878`: build, health 200, unauthenticated MCP 401, and bounded graceful shutdown all passed |

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
- This Phase 1 note is historical. Phase 3 subsequently repaired the site and audit
  isolation defects and produced fully green run `29703827878`.

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

## Phase 3 burn-in and rc4 candidate

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
- The operator-approved burn-in culminated in GitHub run `29703827878` at exact
  commit `790ef5d9e5afa5baa6ae2093f318c2d40ca971ff`. All 12 jobs passed: nine
  Python 3.11-3.13 cells across Ubuntu, Windows, and macOS, package/SBOM/SARIF/site,
  isolated wheel dependency audit, and container lifecycle. Every matrix cell
  passed 175 tests, Ruff, strict mypy, 88% branch coverage, acceptance, and
  compliance; the CI jobs emitted zero annotations.
- The run URL is
  `https://github.com/DDYRich72/UpToCode/actions/runs/29703827878`.
- A fresh Ubuntu/WSL clone at `790ef5d` (Python 3.12.3, Node 22.22.2) passed 175
  tests, acceptance, compliance, Ruff, strict mypy over 30 files, 88% branch
  coverage, clean npm installation of 508 packages, ESLint, `tsc --noEmit`, the
  `/` and `/connect` production build, and two rendered-route tests.
- The same WSL clone completed the offline terminal/JSON/HTML/review/FIXPLAN/
  compliance demo. The critical scan returned 1 as designed; artifact-producing
  commands returned 0. Generated artifacts were removed and the tree was clean.
- A separate fresh Windows clone at `790ef5d` (Node 24.14.1) completed a clean npm
  installation of 507 packages, ESLint, `tsc --noEmit`, the production build, and
  both route tests, then returned to a clean tree. Clean Windows Python evidence
  comes from the three successful Windows matrix cells in run `29703827878`.
- PyPI publication was removed from the release-candidate workflow in accordance
  with D006. Tagged private-repository builds retain artifacts and SBOMs but skip
  GitHub attestation because that feature is unavailable for user-owned private
  repositories; signed/attested publication is deferred to Phase 7.
