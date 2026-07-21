# Validation Report

## Batch 2 audience expansion — 2026-07-20

Status: **local implementation gate passed; operator-hosted CI/release actions pending**.

### Acceptance mapping

- **Shared evidence and Python adapters — passed.** Language-neutral loop, model-call,
  tool, budget, resilience, enforcement, validation, and observability evidence feeds the
  existing AA evaluators. Anthropic, CrewAI, PydanticAI, and LlamaIndex bad/clean fixtures
  and positive/clean/suppression/unsupported/false-positive tests pass.
- **TypeScript subset and Report 2.2 — passed locally.** Tree-sitter parses `.ts`, `.tsx`,
  and `.mts`; mixed repositories expose strict per-language coverage; syntax recovery and
  dynamic configuration warn; CLI/reporters/review/MCP accept the new contract.
- **Parser wheel matrix — configured, external confirmation pending.** Windows/Python 3.13
  installed `tree-sitter 0.26.0` and `tree-sitter-typescript 0.23.2` successfully. CI now
  parses TypeScript explicitly in all Python 3.11-3.13 x Ubuntu/Windows/macOS cells.
- **Interactive HTML review — passed.** CSP, hostile JSON escaping, accessible decision
  controls, manifest model shape/order, and no-network assertions pass. Browser dry-run
  approved one finding, rejected one, downloaded ReviewManifest 2.0, and successfully ran
  `uptocode plan` against JSON emitted from the same scan via `--json-output`.
- **Version/docs contract — passed.** Package/runtime/server versions agree at 1.7.0;
  CHANGELOG records the fixed 1.2.0-1.7.0 sequence; specs, decisions, framework memos,
  README, architecture, roadmap, and current-state claims match implemented behavior.

### Local evidence

```text
python -m pytest -q                         221 passed
python scripts/acceptance.py                PASS
python scripts/compliance.py                PASS (0 findings/warnings/suppressions)
python -m ruff check uptocode tests scripts PASS
python -m mypy uptocode                     PASS (40 source files)
coverage --branch                           87% (minimum 85%)
web npm test                                7 passed; production build passed
interactive HTML → manifest → plan          PASS
```

The site test used the existing dependency installation in the original workspace
because a fresh `npm ci` in the isolated worktree timed out; the tracked `web/` tree is
unchanged between those worktrees. No tag, package publication, deployment, paid API call,
or production-data action was performed.

Phase 5 is deployed to the approved Cloud Run project and region. Corrective commit
`44e9d46` passed targeted hosted tests, Ruff, and strict mypy before Cloud Build produced
immutable image digest `sha256:298fadd434cafc4a28182a4f263ca1a2b23c2aea0d02627ac9aebe3046bd778d`.
The pre-rename Cloud Run revision passed the no-paid-call live smoke and payload-free-log
verification. The complete `rc6` clean-clone exit gate is recorded below after deployment;
the UpToCode production migration remains a separate Phase 7 checkpoint.

## Reference production gates

| Gate | Status | Evidence |
|---|---|---|
| Python suite | PASS | Exact rc6 commit `f578f24` fresh Windows and Ubuntu/WSL clones: `python -m pytest -q` → 186 passed; exact rc6 nine-cell tag CI `29717587213` also passed |
| Offline product acceptance | PASS | Exact rc6 commit `f578f24` clean clones and all nine tag-CI cells: 186 tests, real installed-process stdio MCP, malformed-call recovery, CLI/report/review/plan/non-mutation, clean/bad fixtures |
| Production dogfood | PASS | Fresh clones on both platforms: zero production findings, zero suppressions, zero analysis warnings; `.uptocode/architecture-compliance.json` |
| Ruff | PASS | Fresh clones on both platforms: all checks passed |
| Strict typing | PASS | All nine GitHub cells: no issues in 30 source files |
| Branch coverage | PASS | All nine GitHub cells: 88%, exceeding the configured 85% release floor |
| Wheel | PASS | `uptocode-1.0.0-py3-none-any.whl` built, installed in an isolated environment, imported from site-packages, and exercised through stdio MCP |
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
| Container lifecycle | PASS | Exact rc6 tag CI `29717587213`: build, health 200, unauthenticated MCP 401, and bounded graceful shutdown all passed |

## Safety and external actions

- Static analysis makes no network calls and submitted-source temporary directories are removed after each request.
- Source, prompts, keys, email addresses, and SSNs are absent from captured judgment failure logs; hosted operational logs are payload-free by policy and implementation.
- Review and FIXPLAN generation do not modify scanned repositories.
- The operator explicitly authorized Cloud Run deployment and judge-key generation. No
  package publication, site deployment, credential distribution, public repository release,
  submission, or new paid model request was performed.
- The historical single authorized synthetic GPT-5.6 smoke remains recorded in `.uptocode/live-smoke.json`; a post-build/post-deploy smoke requires fresh explicit approval.

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
  `uptocode-1.0.0-py3-none-any.whl`, passes `pip check`, and reports no known
  dependency vulnerabilities. The unpublished UpToCode package itself is
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

## Phase 5 live hosted verification

- Project `gen-lang-client-0606364192` and region `us-central1` were used under explicit
  operator approval. Exact superseded service and identity names remain in the immutable
  submission tag rather than being advertised as current UpToCode resources.
- Cloud Build `d013ca7f-ca25-4b66-89f8-93c49ef65315` built commit `44e9d46` from archive
  SHA-256 `16990989e2a2067d95e7d8b4652f2ce7cdae1d61628e169b45cb8dd98f14d8aa` and pushed
  immutable image digest `sha256:298fadd434cafc4a28182a4f263ca1a2b23c2aea0d02627ac9aebe3046bd778d`.
- The pre-production Cloud Run revision received 100% of its service traffic and used the digest-only
  Secret Manager allowlist, rate limit `30`, hosted judgment `false`, exact Host-header
  allowlisting, and no `OPENAI_API_KEY`.
- Sanitized live evidence in ignored `.uptocode/` records version `1.0.0`, eight
  hosted tools, readiness PASS, unauthenticated MCP `401`, AA001 PASS, judgment-gate PASS,
  `429` with `Retry-After` PASS, and zero paid model calls.
- Exported Cloud Run logs passed the verifier: safe eight-character key attribution was
  present while the raw credential, full digest, and submitted sentinel were absent.
- The raw judge key remains outside the repository and has not been printed, committed,
  pushed, or distributed. The operator approved and pushed `v1.0.0-rc6`; credential
  distribution remains a separate operator-only submission action.

## Phase 5 submission-ready exit gate

- Exact commit `ab06ff1` was cloned independently on Windows and Ubuntu/WSL. Windows used
  Python 3.13.7 and Node 24.14.1; WSL used Python 3.13.12 and Node 22.22.2.
- Both clean clones passed 186 tests, installed-process acceptance, zero-finding production
  compliance, Ruff, strict mypy over 30 source files, and 88% branch coverage.
- Windows installed 493 site packages and WSL installed 494 platform-adjusted packages.
  Both passed ESLint, `tsc --noEmit`, the production build for exactly `/` and `/connect`,
  five site tests, and the high-severity npm release threshold. The two documented moderate
  Next/PostCSS records remain the dated accepted risk in `SECURITY.md`.
- The offline demo passed on both platforms: the deliberate fixture produced the expected
  critical exit 1, ten findings, three redactions, three bound review decisions, and an
  approved-only FIXPLAN. Acceptance independently verified fixture non-mutation and the real
  ten-tool stdio MCP lifecycle.
- Both post-gate Git trees were clean. Claims match the live eight-tool hosted surface and
  the exact remote. No push, tag, credential distribution, video upload, submission, package
  publication, repository-access change, or paid model call occurred during the exit gate.

## Phase 6 submission preparation

- Published rc6 tag `v1.0.0-rc6` resolves to exact commit `f578f24`. That candidate was
  cloned independently on Windows and Ubuntu/WSL and repeated the complete submission gate:
  186 tests, acceptance, compliance, Ruff, strict mypy over 30 source files, 88% branch
  coverage, clean site install/lint/type/build/five tests, offline demo, and clean trees.
- Exact rc6 branch CI `29717585938` and tag CI `29717587213` passed every nine-cell
  Python/OS job plus package/site, isolated wheel audit, and container lifecycle checks.
  Release-artifact run `29717587195` passed the same release gates and retained the wheel,
  distributions, SBOMs, compliance evidence, and private-repository attestation deferral.
- The initial workflow attempts were rejected before runner allocation by an account billing
  hold. Attempt 6 passed after the operator corrected the personal Actions billing owner;
  this was external account state, not a repository defect.
- Annotated tag `v1.0.0-submission` and commit `8d822f0` were pushed after operator
  approval. Branch CI `29720149185`, tag CI `29720149466`, and release-artifact run
  `29720149370` all passed on exact commit
  `8d822f02c76ba9c30a4da665d80b7fb77201fdf4`.
- Private-repository sharing, judge-key distribution, public video upload, Devpost
  submission, and submitted URL/timestamp remain operator-only actions.

## Phase 7 UpToCode production preparation

- Exact verified implementation commit: `ef126c6` (`refactor: establish UpToCode
  production identity`). Fresh local Windows and WSL clones checked out that commit and
  finished with clean Git trees.
- D008, `specs/003-uptocode-production-identity.md`, and
  `tasks/phase7-production-plan.md` define one canonical identity: product UpToCode;
  distribution/import/CLI `uptocode`; settings `UPTOCODE_*`; MCP Registry name
  `io.github.DDYRich72/uptocode`; hosted resources `uptocode-mcp`.
- Current tracked files contain no superseded product identifier. Historical evidence is
  preserved by immutable Git history and tags rather than repeated in current claims.
- Official PyPI JSON endpoints and `pip index versions` returned no project for `uptocode`
  or `uptocode-audit` on 2026-07-20. Availability remains race-prone and must be checked
  again immediately before publication.
- `server.json` includes the GitHub-auth namespace, stable repository ID `1305781548`,
  explicit `uvx` package arguments, and the required README `mcp-name` ownership marker.
  The manifest passed the official 2025-12-11 MCP Registry JSON schema fetched from
  `static.modelcontextprotocol.io`.
- Production release automation builds and verifies once, retains package/SBOM/compliance
  artifacts, and isolates attestation plus PyPI OIDC publication in the protected `pypi`
  environment. Exact-version tag verification and the public-repository guard prevent RC
  or private-repository publication.
- An isolated Windows wheel environment installed `uptocode-1.0.0`, agreed on runtime and
  metadata version `1.0.0`, and passed `pip check`. The wheel is 58,838 bytes.
- Packaging inspection caught workspace/build output in the initial sdist (14.6 MB and
  8,327 files). An explicit Hatch sdist allowlist reduced the verified archive to 47,945
  bytes and 40 intentional public-package files; tests prohibit web/docs/tests/cache input.
- Windows: Python 3.13.7; 188 tests, offline acceptance, compliance, Ruff, strict mypy over
  30 files, and 88% branch coverage pass. A Git-tracked-only site copy installed 493
  packages offline and passed ESLint, `tsc --noEmit`, the `/` and `/connect` production
  build, five rendered-route tests, and the high-severity npm threshold.
- POSIX/WSL: Python 3.13.12 in a fresh `uv` venv; the same 188-test Python gates and 88%
  coverage pass. A Git-tracked-only site copy installed 494 packages and passed the same
  site gates. Both platforms report only the two dated moderate Next/PostCSS records
  accepted in `SECURITY.md`.
- Local Docker was unavailable during preparation; GitHub CI supplied the container gate.
  Google Cloud CLI 576.0.0 was installed only after explicit migration approval. No package
  publication, repository visibility change, registry submission, credential distribution,
  or paid model call occurred.
- The operator-approved production-branch push placed `codex/uptocode-production` at
  `6918b49`. GitHub CI run `29725081460` completed successfully against that exact commit:
  all nine Python 3.11-3.13/Linux-macOS-Windows cells, package/SBOM/SARIF/site, isolated
  wheel audit, and container health/auth/shutdown jobs passed. This closes the local-Docker
  coverage gap without a rerun.
- The approved migration created the `uptocode` Artifact Registry repository,
  `uptocode-mcp-runtime` service account, and `uptocode-api-key-hashes` digest-only secret.
  Cloud Build `21c2abda-1c59-4148-b54f-ff1acb486f43` built the exact `1394c7f` archive and
  pushed image digest
  `sha256:309f90c591b1072dacc16726366f4319fd4996c2b4cdb9230c37d14c94e12091`.
- Cloud Run revision `uptocode-mcp-00001-szq` receives 100% of traffic at
  `https://uptocode-mcp-1015314816960.us-central1.run.app/mcp`. It uses the dedicated
  runtime identity and secret, rate limit `30`, ingress `all`, application-level bearer
  authentication, hosted judgment `false`, and no `OPENAI_API_KEY`.
- The live no-paid smoke passed version `1.0.0`, readiness, unauthenticated `401`, eight-tool
  hosted discovery, AA001, judgment-gate rejection, and `429` with `Retry-After: 2`.
  Exported logs contain only safe key ID `f7254b8f`; the raw key, full digest, and submitted
  synthetic sentinel are absent. The smoke made zero paid model calls.
- The synchronized `server.json` with the verified `streamable-http` remote validates
  against the official 2025-12-11 MCP Registry schema. The hosted key is represented only
  as required secret variable `UPTOCODE_API_KEY`; no credential value is present.
- The post-migration Windows gate passes 188 tests, 88% branch coverage, offline
  acceptance, production compliance, Ruff, and strict mypy over 30 files. A clean
  Git-tracked site copy under Node 22.19.0 installed 493 packages and passed ESLint,
  `tsc --noEmit`, the `/` and `/connect` build, all five site tests, and the existing
  high-severity npm threshold. The dated two-moderate advisory record remains unchanged.
- Fresh release artifacts build successfully after endpoint synchronization:
  `uptocode-1.0.0-py3-none-any.whl` is 58,893 bytes and
  `uptocode-1.0.0.tar.gz` is 48,410 bytes. An isolated environment reports version `1.0.0`
  through both entry points and passes `pip check`.
- GitHub CI run `29753128316` passed the complete matrix, package/site/wheel, and container
  jobs on exact pushed checkpoint `1394c7f`. No additional CI run was started during the
  local claim-synchronization gate.
- At this pre-publication checkpoint GitHub remained private with the frozen submission
  branch as default. The production branch was available remotely, while the protected
  `pypi` environment and trusted-publisher relationship had not yet been created. Official
  PyPI JSON lookups for `uptocode` and `uptocode-audit` returned 404 at that checkpoint.
- The external credential files were renamed in place to
  `C:\Users\nokes\.uptocode-secrets\uptocode-production-key.{txt,sha256}` without reading,
  printing, replacing, or distributing the credential.

## Phase 7 public production release

- Operator approved the combined Stage 4 sequence on 2026-07-20. GitHub repository
  `DDYRich72/UpToCode` is public and defaults to `codex/uptocode-production`; the frozen
  submission tag remains unchanged.
- The protected `pypi` environment requires operator review and admits only exact tag
  `v1.0.0`. PyPI pending publisher identity was exactly `DDYRich72/UpToCode`, workflow
  `release.yml`, environment `pypi`, and project `uptocode`.
- `uptocode` returned 404 immediately before the annotated `v1.0.0` tag was created at
  `fc458948ac9391d08d7d84a1eac0d81e41d126a3` and pushed.
- Production release run `29761626504` passed the full release gate, built once, retained
  package/SBOM/compliance evidence, and published through GitHub OIDC after protected
  environment approval. Tag CI run `29761626642` passed all nine Python cells plus the
  package/site, isolated wheel-audit, and container lifecycle jobs.
- PyPI serves `uptocode==1.0.0`: wheel 58,893 bytes with SHA-256
  `34d53e778ca4219d3f853fcb133c1782f06fd85e053d0dcf21ee046fd3b4b2dc`; sdist
  48,410 bytes with SHA-256
  `b84c0bcdac6bb8dbc46f534e665608e4567499f2576b21cf2fa7c82bddca33fa`.
  GitHub attestation verification bound both digests to
  `.github/workflows/release.yml`, source ref `refs/tags/v1.0.0`, and this repository.
- A fresh Python 3.13 environment installed `uptocode==1.0.0` from the public index;
  `uptocode --version` and `python -m uptocode --version` both returned `1.0.0`, and
  `pip check` reported no broken requirements.
- Official `mcp-publisher` v1.7.9 Windows AMD64 archive matched release SHA-256
  `aa7c3e014a38b427171b5c6d2c034551daa6fd822ce4a00d1dee2dbf7a21c118`.
  Its live validation passed before publication. The Registry API now returns one active,
  latest `io.github.DDYRich72/uptocode` record at version `1.0.0`, published
  `2026-07-20T17:04:57.809548Z`, with the PyPI package and verified Cloud Run remote.
- No credential was distributed and no paid model call was made during Stage 4.

## Batch 1 — Quick Wins / 1.1.0 implementation

- **PASS — contracts:** `SPEC.md` defines Report/Baseline 2.1, structured citations,
  stable/experimental maturity, inclusive suppression expiry, share-safe rendering, and
  AA013 before implementation. Runtime, package, and MCP manifest versions agree at 1.1.0.
- **PASS — Lane A:** stable AA013 requires proven append/model-input/loop evidence and
  recognizes all specified truncation forms; inconclusive identity emits a coverage
  warning. AA007 distinguishes timeout, retry, and retry-without-backoff. AA001 remediation
  is protocol-aware. Bad/clean fixtures and the deliberate fingerprint golden cover AA013.
- **PASS — Lane B:** Baseline 2.1 classifies new/aging/resolved debt, upgrades 2.0 input,
  and preserves `first_seen` through combined apply/update. Structured suppression tests
  cover bare/full/malformed and yesterday/today/tomorrow. Share-safe JSON, HTML, and SARIF
  contain no tested Windows, UNC, Linux-home, macOS-home, or scan-root path sentinels.
- **PASS — registry/reporting:** every emitted fixture finding carries the complete
  registry citation set; AA004 contains OpenAI and Anthropic records; legacy `vendor`
  input remains readable; no placeholder citation labels remain. Experimental maturity is
  visible in terminal, JSON, HTML, GitHub, SARIF, and MCP metadata and affects thresholds
  only with `--include-experimental`.
- **PASS — adoption:** the exact pre-commit hook contract, PyPI badge, copyable scan badge,
  README rule/CLI documentation, CHANGELOG, architecture docs, and AA013 site surface are
  present. MCP Registry 1.0 publication is treated as already complete; no resubmission was
  attempted.
- **PASS — Windows gate (Python 3.13.7 / Node 22.19.0):** 207 tests, offline acceptance,
  production compliance, Ruff, strict mypy over 32 source files, 88% branch coverage, site
  build, and all seven site tests pass.
- **PASS — POSIX/WSL gate (Python 3.13.12 / Node 22.22.2):** a fresh Python 3.13
  environment passes 207 tests, offline acceptance, production compliance, Ruff, strict
  mypy over 32 source files, and 88% branch coverage. A clean isolated Linux `npm ci`
  installed 495 packages and passed the site build and all seven tests.
- The WSL hosted lifecycle initially exposed a cold mounted-filesystem import time longer
  than the test's approximately five-second retry window. Replacing the iteration count
  with an explicit 30-second startup deadline made the test deterministic; the lifecycle
  subsequently passed in the targeted and full POSIX runs.
- Production dogfood reports zero findings, zero suppressions, and zero unexplained
  warnings. No paid model call, deployment, publication, Marketplace mutation, GitHub
  Release creation, tag creation/push, or credential operation occurred.
- **OPERATOR GATES REMAIN:** create the missing `v1.0.0` GitHub Release, list the Action on
  GitHub Marketplace, then create/push `v1.1.0` only after reviewing these local changes.

## Batch 3 Lane 3.1 — Isolated remediation / 1.8.0

- **PASS — approval contract:** D012 records operator approval; scan/review/plan and fix
  preview remain non-mutating, while `fix --apply` delegates only to an external runner in
  retained per-fingerprint branches/worktrees.
- **PASS — implementation:** strict `FixSession`/`FixResult` evidence records runner exit,
  fingerprint absence, verification status, branch, worktree, and final PASS/FAIL.
- **PASS — offline tests:** fake runners cover no-write dry-run, clean-tree refusal, stale
  findings, argv placeholders, successful isolation, runner failure, and retained work.
- **PASS — Windows gate:** Ruff, strict mypy over 41 source files, 225 tests, 87% branch
  coverage, offline acceptance, production compliance, site build, and all seven site tests
  pass. No live runner, model call, merge, publication, or tag operation was performed.

## Batch 3 Lane 3.2 — MCP architecture and control rules / 1.9.0

- **PASS — stable controls:** AA014 recognizes authenticated FastMCP network transports,
  AA015 requires explicit tool annotations, and AA016 requires strict argument schemas.
  Stdio is not applicable and unresolved transport/composition evidence is reported as a
  coverage warning rather than a clean result.
- **PASS — experimental controls:** AA017 detects undifferentiated generic tool failures
  and AA018 detects prompt-only critical prerequisites. Ambiguous cases are nominated for
  judgment; experimental findings remain outside thresholds unless explicitly included.
- **PASS — evidence:** dedicated bad/clean MCP fixtures and 11 focused tests cover positive,
  clean, suppression, stdio, dynamic, false-positive, registry, and judgment-candidate
  behavior. The compliance map now covers AA001-AA018.
- **PASS — Windows gate:** Ruff, strict mypy over 41 production modules, 236 tests, 87%
  branch coverage, offline acceptance, zero-finding production compliance, site build, and
  all seven site tests pass. No live model, release, publication, deployment, or tag action
  was performed.

## Batch 3 Lane 3.3 — VS Code diagnostics / 1.10.0

- **PASS — thin client:** the standalone TypeScript/esbuild workspace scans only saved or
  explicitly requested Python files, reserves JSON/threshold output flags, and accepts
  valid report exits 0 and 1 without adding a daemon, LSP, repository scan, code action,
  or auto-fix.
- **PASS — diagnostics:** critical/warning/info severity, rule code, first citation,
  one-based full-line ranges, observed evidence, and experimental status are mapped.
  Clean/failed scans clear stale diagnostics, analysis warnings reach the output channel,
  and per-document generations prevent rapid-save races.
- **PASS — extension gate:** strict TypeScript checking, nine Vitest tests, esbuild bundle,
  and `@vscode/vsce` packaging produce a local 9.74 KB VSIX. CI has a separate Node 22
  lockfile-scoped job; Marketplace listing and publication remain operator-only.

## Batch 4.1 — Full LSP integration / 1.11.0

- **PASS — approval and scope:** the operator acknowledged spec 006 and D013 before RED
  tests or implementation. The only new mutation is an explicit, metadata-validated,
  version-checked suppression edit in the active document; it does not auto-save.
- **PASS — persistent protocol:** `uptocode lsp` completes initialize, incremental sync,
  open/save diagnostics, close clearing, shutdown, and exit through the pytest-lsp client
  harness. Scans run outside the protocol loop, remain file-scoped and static-only, and
  generation checks reject stale results.
- **PASS — parity and actions:** parameterized fixtures cover every default static rule
  AA001-AA004, AA006-AA007, and AA010-AA018; AA005/AA008/AA009 remain `not_requested`.
  Python and TypeScript suppression round-trips, citation payloads, exact-fingerprint and
  missing/stale FIXPLAN states, multi-root selection, spaced paths, malformed source,
  unsupported URIs, and bounded failure logs pass.
- **PASS — latency:** the checked-in 492-line fixture completed 20 warm file-analysis
  cycles at 144.61 ms p95 on Windows and 45.80 ms p95 on POSIX, below the 200 ms budget.
- **PASS — Windows gate:** 264 tests, offline acceptance, production compliance, Ruff,
  strict mypy over 42 modules, and 87% branch coverage pass. Site lint/type/build and all
  seven tests pass. A clean temporary npm install passes extension typecheck, four action
  tests, esbuild, and VSIX packaging (334.44 KB). The 1.11.0 wheel/sdist build and an
  isolated wheel install pass version agreement and `pip check`.
- **PASS — POSIX gate:** an exact tracked working-tree snapshot passes 264 tests, offline
  acceptance, compliance, Ruff, strict mypy, 87% branch coverage, the latency budget,
  clean extension install/typecheck/tests/build/VSIX, and clean site install/lint/type/build
  with all seven tests.
- **OPERATOR GATES REMAIN:** the operator authorized the reviewed Batch 4.1 branch commit
  and push on 2026-07-21. No `v1.11.0` tag, PyPI release, VS Code Marketplace publication,
  deployment, credential operation, network judgment, or paid model call was performed.
  Batch 4 stops here pending demand reassessment before selecting 4.2–4.5.
