# Validation Report

Phase 5 deployment-preparation commit `a76ce14` passed the complete Windows and Ubuntu/WSL
clean-clone gate and offline demo dry-run. Phase 4 is preserved as `v1.0.0-rc5` at
`752bb02`; branch CI `29710990279`, exact-tag CI `29710992278`, and release-artifact run
`29710992277` passed. No Cloud Run service or judge credential exists yet, so this is a
pre-deployment checkpoint rather than the `rc6` exit gate.

## Reference production gates

| Gate | Status | Evidence |
|---|---|---|
| Python suite | PASS | Phase 5 fresh Windows and Ubuntu/WSL clones: `python -m pytest -q` → 184 passed; latest published rc5 nine-cell CI remains 175 passed in every cell |
| Offline product acceptance | PASS | Phase 5 clean clones: 184 tests, real installed-process stdio MCP, malformed-call recovery, CLI/report/review/plan/non-mutation, clean/bad fixtures |
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
| Functional site | PASS | Fresh Windows and Ubuntu/WSL clones build `/` and `/connect`; five rendered/contract tests pass. Real Worker delivery was browser-verified at desktop and 375px mobile widths with CSS/JS assets returning 200, no console errors or overflow, and working keyboard tabs. |
| Site dependency audit | PASS WITH DATED ACCEPTED RISK | Direct patched dependencies remove all high/critical records. `npm audit --omit=dev --audit-level=high` exits 0 with the two Next/nested-PostCSS records for GHSA-qx2v-qp2m-jg93; exposure, rationale, and 2026-08-02 review date are in `SECURITY.md`. |
| Container lifecycle | PASS | Exact rc5 tag CI `29710992278`: build, health 200, unauthenticated MCP 401, and bounded graceful shutdown all passed |

## Safety and external actions

- Static analysis makes no network calls and submitted-source temporary directories are removed after each request.
- Source, prompts, keys, email addresses, and SSNs are absent from captured judgment failure logs; hosted operational logs are payload-free by policy and implementation.
- Review and FIXPLAN generation do not modify scanned repositories.
- No package publication, site deployment, Cloud Run deployment, judge-key generation,
  public repository release, submission, or new paid model request was performed.
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

## Phase 3 burn-in and rc4

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
  This is historical Phase 3 evidence; Phase 4 subsequently removed the unused
  Drizzle/D1 starter surface and refreshed the site dependency tree.
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

## Phase 4 submission-ready evidence

- Implementation commits `b07a34a` (`feat(web): polish competition surface`) and
  `6e396ea` (`fix(web): ignore TypeScript build state`) were verified from fresh clones.
- Windows (Python 3.13.7, Node 22.19.0) and Ubuntu/WSL (Python 3.13.12, Node 22.22.2)
  each passed 175 tests, offline acceptance, production compliance, Ruff, strict mypy
  over 30 files, and 88% branch coverage.
- Both clean clones completed `npm ci`, ESLint, `tsc --noEmit`, the production build for
  exactly `/` and `/connect`, and five rendered/contract tests. Windows installed 493
  packages; WSL installed 494 because of platform-specific optional dependencies.
- Drizzle/D1 packages, source, binding configuration, migration hooks, examples, starter
  assets, and generic starter documentation are absent. The tracked Sites plugin remains
  and packages only the empty hosting manifest.
- Patched Cloudflare/Vite releases eliminate the six previously reported high audit
  records. The production audit has no high or critical findings; its two moderate
  Next/PostCSS records are the dated accepted risk in `SECURITY.md`.
- Browser verification used Wrangler 4.102.0's real asset binding. `/`, `/connect`, RSC,
  CSS, and JavaScript requests returned 200; desktop and 375px mobile views had no error
  overlay, console error, or horizontal overflow. Arrow-key tabs moved selection and focus
  from Local stdio to Hosted MCP, which displayed `<HOSTED_MCP_URL>` rather than a fake
  deployment. No password/key input exists.
- The offline demo sequence passed in both exact-commit clones. The deliberate bad fixture
  produced ten findings and three redactions; JSON, standalone HTML, report-bound review,
  approved-only FIXPLAN, and compliance commands succeeded. Both Git trees remained clean.
- The three Phase 4 commits and annotated `v1.0.0-rc5` tag were pushed with explicit
  operator approval. Branch CI `29710990279`, tag CI `29710992278`, and release-artifact
  run `29710992277` all completed successfully. No deployment, repository access change,
  publication, credential distribution, video upload, paid model call, or submission
  occurred during Phase 4.

## Phase 5 pre-deployment checkpoint

- Exact preparation commit `a76ce14` was cloned independently on Windows and Ubuntu/WSL.
  Windows used Python 3.13.7 and Node 22.19.0; WSL used Python 3.13.12 and Node 22.22.2.
- Both clean clones passed 184 tests, offline acceptance, production compliance, Ruff,
  strict mypy over 30 source files, and 88% branch coverage.
- Windows installed 493 site packages and WSL installed 494 platform-adjusted packages.
  Both passed ESLint, `tsc --noEmit`, the production build for exactly `/` and `/connect`,
  five site tests, and the high-severity npm release threshold. The two moderate
  Next/PostCSS records remain the dated accepted risk in `SECURITY.md`.
- The offline demo dry-run passed in both clones. The deliberate fixture returned the
  expected critical exit 1, ten findings, three redactions, three bound review decisions,
  an approved-only FIXPLAN, zero-finding compliance, and an unchanged fixture hash.
- Targeted deployment/MCP tests validate immutable digest rendering, placeholder
  rejection, application-bearer Cloud Run annotations, omission of `OPENAI_API_KEY`,
  explicit refusal without key/live-test authorization, and log checks that require safe
  eight-character attribution while rejecting raw keys, full digests, and submitted
  sentinels.
- `scripts/render_cloud_run.py` produced a validated secret-free example locally and
  explicitly performed no deployment or credential operation.
- The current Windows environment has no Google Cloud CLI or Docker. GitHub exposes only
  the existing `release-approval` environment and no GCP repository variables or secrets.
  A real project, region, authenticated deployment path, judge key, endpoint, live smoke,
  log export, and `server.json` remote remain outstanding.
- No external mutation occurred in this checkpoint: no push, tag, Cloud Run resource,
  key generation/distribution, remote-access change, video upload, submission, or paid
  model call.
