# Progress

## Current gate

Completion Plan v2 Phase 7 — UpToCode production release and publication.
Repository visibility, package publication, registry submission, credential distribution,
and paid-model use remain operator-controlled.

## Status

- [x] Operator declared UpToCode the canonical identity for the program and MCP; D008 and
  `specs/003-uptocode-production-identity.md` record the complete public contract.
- [x] Post-submission work moved to `codex/uptocode-production`; the submitted branch and
  immutable `v1.0.0-submission` tag remain frozen at `8d822f0`.
- [x] Distribution, import, CLI, config/output paths, environment variables, reports,
  Action, site, container, deployment templates, MCP manifest, tests, and documentation
  migrated to UpToCode with no superseded identifier in the current tracked surface.
- [x] `uptocode` and `uptocode-audit` were absent from the official PyPI index on
  2026-07-20; `uptocode` is the selected distribution and will be rechecked at publish time.
- [x] Official MCP metadata uses `io.github.DDYRich72/uptocode`, the stable GitHub
  repository ID, explicit `uvx` arguments, and the required PyPI README ownership marker;
  it passed the live 2025-12-11 official JSON schema.
- [x] Production release automation separates verified builds from the protected `pypi`
  OIDC job, SHA-pins external Actions, attests packages, and rejects non-exact tags.
- [x] The source archive allowlist fixed an audit-discovered packaging defect: the sdist
  dropped from 14.6 MB/8,327 workspace files to 47,945 bytes/40 intentional files.
- [x] Clean isolated wheel install passed version agreement and `pip check`; wheel size is
  58,838 bytes.
- [x] Phase 7 Windows and POSIX gates pass: 188 tests, acceptance, compliance, Ruff,
  strict mypy over 30 files, 88% branch coverage, clean site installs, lint/type/build,
  five site tests, and the high-severity npm threshold.
- [x] Exact implementation commit `ef126c6` repeated that complete gate from fresh local
  Windows and WSL clones; both post-gate trees were clean.
- [x] Separate unimplemented 1.1 specifications added for Firestore beta access control
  and TypeScript analysis.
- [x] The production branch is pushed at `6918b49`; GitHub CI run `29725081460` passed the
  complete nine-cell Python matrix, package/site/wheel jobs, and renamed container health,
  unauthorized-MCP, and graceful-shutdown lifecycle on 2026-07-20.
- [x] Operator-approved Cloud migration built exact commit `1394c7f` as immutable digest
  `sha256:309f90c591b1072dacc16726366f4319fd4996c2b4cdb9230c37d14c94e12091`
  and deployed `uptocode-mcp-00001-szq`; all no-paid hosted and log-safety checks pass.
- [x] Post-migration gate passes locally: 188 tests, 88% branch coverage, acceptance,
  compliance, Ruff, strict mypy over 30 files, official MCP Registry schema validation,
  clean 493-package site install, lint, `tsc --noEmit`, build, five site tests, wheel/sdist
  build, isolated install, version agreement, and `pip check`. Push CI `29753128316` is
  also fully green on exact checkpoint `1394c7f`.
- [ ] Operator checkpoints: make the repository public and select the UpToCode production
  default branch; configure the protected `pypi` environment and trusted publisher;
  publish `v1.0.0`; submit the MCP Registry record; distribute credentials only through
  an approved private channel; and separately approve any additional paid smoke call.
- [x] Approved `SPEC.md` and `GOAL.md` copied into the repository.
- [x] Durable project documents drafted.
- [x] Package/import smoke test (`python -m pytest -q tests/test_bootstrap.py`: 1 passed).
- [x] Gate 1 implementation and validation (`python -m pytest -q`: 13 passed).
- [x] Gate 2 rule engine, judgment candidate extraction, fixtures, goldens, and validation (`python -m pytest -q`: 49 passed).
- [x] Gate 3 judgment, review/plan, standalone HTML, and MCP surfaces (`python -m pytest -q`: 71 passed).
- [x] Gate 4 README, demo/submission drafts, cross-platform acceptance runner, and self-scan triage.
- [x] Rendered HTML visual inspection approved by the user.
- [x] One explicitly authorized GPT-5.6 live smoke completed successfully.
- [x] Final clean-worktree completion audit.
- [x] Fresh-clone Sites build defect fixed by moving the required Vite plugin to a
  tracked path (`6931eaa`).
- [x] Completion Plan v2 and D005-D007 committed without rewriting published history
  (`a601396`).
- [x] Phase 0 clean-clone gate passed on Windows and Ubuntu/WSL: 158 tests,
  acceptance, compliance, Ruff, strict mypy, 86% branch coverage, and two site tests.
- [x] Phase 0 offline demo commands dry-run successfully.
- [x] Phase 0 evidence recorded for the verification commit.
- [x] Phase 0 commits pushed and annotated `v1.0.0-rc1` published after explicit
  operator approval; the private repository remains private.
- [x] Event-rules ownership/evidence checklist added.
- [x] README judge test-build instructions and “Built with Codex and GPT-5.6”
  disclosure added.
- [x] Sub-three-minute demo script synchronized to six product beats plus the
  explicit Codex/GPT-5.6 development beat, narration, and IP guardrails.
- [x] Devpost draft synchronized to the ten-tool local MCP, hosted subset, SARIF,
  baselines, changed-since, rule selection, review, and FIXPLAN surfaces.
- [x] Sanitized submission evidence committed: terminal/HTML/JSON reports, AA006
  redaction, bound review manifest, FIXPLAN, real stdio MCP response, acceptance,
  and validation matrix.
- [x] Phase 1 clean-clone gate passed on Windows and Ubuntu/WSL: 158 tests,
  acceptance, compliance, Ruff, strict mypy, 86% branch coverage, and two site tests.
- [x] Phase 1 offline demo sequence dry-run successfully from the exact commit.
- [x] Operator captured the Codex Session IDs outside the repository.
- [x] Phase 1 commits and annotated `v1.0.0-rc2` pushed after explicit operator
  approval; the private repository remains private.
- [x] Effective local root resolved once per MCP server and enforced for every
  file, repository, and diff-base path.
- [x] FastMCP 1.28.1 strict-schema compatibility shim guarded with an exact SDK
  canary and installed-version fail-closed diagnostics.
- [x] Unused judgment parameters removed from `check_tool_schema`.
- [x] Hosted per-key token-bucket limiting added with monotonic refill, bounded
  idle eviction, `429`/`Retry-After`, and safe digest-prefix attribution.
- [x] Hosted judgment defaults off and is accepted only when
  `UPTOCODE_HOSTED_JUDGMENT=true` globally.
- [x] Package, runtime, and `server.json` version agreement enforced by tests and
  compliance.
- [x] Phase 2 containment, rate-limit, judgment-gate, log-safety, malformed-SDK,
  and version-sync tests added.
- [x] Phase 2 clean-clone gate passed on Windows and Ubuntu/WSL: 167 tests,
  acceptance, compliance, Ruff, strict mypy, 87% branch coverage, clean site
  installs, and two rendered-route tests.
- [x] Phase 2 offline demo sequence dry-run successfully from the exact commit.
- [x] Phase 2 commits pushed and annotated `v1.0.0-rc3` published after explicit
  operator approval; the private repository remains private.
- [x] Dependency auditing separated from the nine-cell test matrix and moved to an
  upgraded isolated wheel-installed environment.
- [x] CI concurrency cancellation and job timeouts added; coverage, validation,
  wheel, distribution, SBOM, and SARIF artifacts retained.
- [x] Site ESLint and `tsc --noEmit` gates added and validated locally.
- [x] Docker health, unauthorized MCP, and graceful-shutdown smoke steps added and
  passed on GitHub's Linux runner.
- [x] Dedicated GitHub reporter escapes hostile message and property data and emits
  a bounded Markdown job summary.
- [x] SARIF omits absent keys and JSON nulls, declares per-rule default levels, and
  retains stable fingerprints.
- [x] Composite Action supports `path`, `fail-on`, `version`, and `upload-sarif`,
  uploads SARIF with `always()` before returning the captured scanner exit code.
- [x] External Actions SHA-pinned and weekly Actions/pip/npm Dependabot configured.
- [x] Full local Phase 3 validation completed and the burn-in candidate committed.
- [x] Operator-approved burn-in completed: all nine Python cells and the package,
  isolated-wheel-audit, and container jobs passed in GitHub run `29703827878`.
- [x] Final clean-environment gate passed on Windows and POSIX, including the
  offline demo dry-run and clean post-gate trees.
- [x] rc4 verification evidence committed locally.
- [x] Operator approved and pushed the rc4 evidence commit and annotated tag.
- [x] Private-repository artifact attestation deferral documented for Phase 7; corrected
  commit `4fe8a61` and replacement `v1.0.0-rc4` tag pushed with operator approval.
- [x] Exact rc4 tag workflows passed again: CI run `29706598903` and release-artifact
  run `29706598904`.
- [x] Unused Drizzle/D1 code, dependencies, migration hooks, examples, starter assets,
  and starter documentation removed; Sites packaging retained without data bindings.
- [x] Direct Cloudflare/Vite/Next/React packages safely updated; the production dependency
  audit reduced from 14 records including six high to the two documented moderate
  Next/PostCSS records.
- [x] Site remains limited to `/` and `/connect`; fake hosted endpoint removed and local
  setup made the honest default.
- [x] Keyboard tabs, visible focus, skip navigation, reduced motion, copy failure status,
  responsive generator layout, and synchronized connection copy implemented.
- [x] 1.0 changelog and self-audit headline synchronized across README, demo, and Devpost.
- [x] Exact Phase 4 implementation commit `6e396ea` passed the complete Windows and
  Ubuntu/WSL gate: 175 tests, acceptance, compliance, Ruff, strict mypy over 30 files,
  88% branch coverage, clean npm installs, and five site tests.
- [x] Exact Phase 4 offline demo sequence passed on Windows and Ubuntu/WSL with ten
  deliberate findings, three redactions, report-bound review, FIXPLAN, and clean trees.
- [x] Worker-delivered `/` and `/connect` verified in a real browser at desktop and
  375px mobile widths: assets 200, no console errors or overflow, keyboard tabs and
  focus movement correct, and no fabricated endpoint or credential field.
- [x] Phase 4 gate evidence recorded for the rc5 candidate.
- [x] The three Phase 4 commits and annotated `v1.0.0-rc5` tag were pushed after
  operator approval; branch CI `29710990279`, tag CI `29710992278`, and release-artifact
  run `29710992277` all passed.
- [x] Phase 5 preparation commit `a76ce14` adds immutable Cloud Run manifest rendering,
  explicit consent-gated judge-key and live-smoke helpers, payload-free log verification,
  and exact hosted judge instructions.
- [x] The Cloud Run template is network-reachable but application-authenticated, leaves
  hosted judgment off, and attaches no `OPENAI_API_KEY`.
- [x] Exact preparation commit `a76ce14` passed fresh Windows and Ubuntu/WSL gates:
  184 tests, acceptance, compliance, Ruff, strict mypy over 30 files, 88% branch
  coverage, clean npm installs, and five site tests.
- [x] The Phase 5 preparation demo sequence passed offline on Windows and Ubuntu/WSL:
  ten deliberate findings, three redactions, three review decisions, FIXPLAN, compliance,
  and fixture non-mutation.
- [x] Operator authorized project `gen-lang-client-0606364192`, region `us-central1`,
  Cloud Run resource creation, judge-key generation, and no-paid-call live verification.
- [x] Cloud Build produced the exact corrective commit image; Cloud Run revision
  `uptocode-mcp-00002-xgh` serves the immutable digest with hosted judgment off and no
  attached OpenAI key.
- [x] Live readiness, unauthorized access, eight-tool discovery, AA001, judgment rejection,
  `429`/`Retry-After`, and payload-free log verification passed with zero paid model calls.
- [x] The exact remote is in `server.json`; site, README, demo, Devpost, current-state, and
  validation claims are synchronized without committing or distributing the raw key.
- [x] Exact commit `ab06ff1` passed the complete Phase 5 clean-clone gate on Windows and
  Ubuntu/WSL: 186 tests, acceptance, compliance, Ruff, strict mypy, 88% branch coverage,
  clean site installs, lint/type/build, five site tests, offline demo, and clean trees.
- [x] The six Phase 5 commits and annotated `v1.0.0-rc6` tag were pushed after explicit
  operator approval; the tag resolves to `f578f24`.
- [x] Exact rc6 commit `f578f24` passed the complete Phase 6 clean-clone gate on Windows
  and Ubuntu/WSL: 186 tests, acceptance, compliance, Ruff, strict mypy, 88% branch
  coverage, clean site installs, lint/type/build, five site tests, offline demo, and clean
  trees.
- [x] Exact rc6 branch CI `29717585938`, tag CI `29717587213`, and release-artifact run
  `29717587195` passed after the personal Actions billing owner was corrected. Earlier
  attempts were rejected before runner allocation and did not execute repository code.
- [ ] Operator checkpoint: approve pushing annotated tag `v1.0.0-submission`, sharing the
  private repository with both judging accounts, distributing the judge key in private
  submission notes, uploading the public demo, and submitting the Devpost entry.

## Notes

- Workspace began as an empty Git repository.
- One paid GPT-5.6 smoke request was explicitly authorized and completed successfully; no further paid requests are authorized.
- The static engine evaluates AA001/2/3/4/6/7/10/11/12 and records AA005/8/9 as judgment-only/not applicable during static scans.
- Semantic HTML, CSP, escaping, redaction, and standalone behavior pass automated tests; the user opened and approved the rendered final HTML report.
- Live evidence: `.uptocode/live-smoke.json` records one synthetic-code request to `gpt-5.6`, a completed structured result, one expected finding, and no analysis warnings. The evidence contains no API key or submitted code.

## Self-scan triage

Latest output: `.uptocode/self-scan.json` from the Phase 4 clean-clone
acceptance run (generated and gitignored).

- Coverage: 53/53 project Python files analyzed with nine excluded-directory records.
  The single whole-repository analysis warning is the known synthetic MCP wiring in
  `scripts/acceptance.py`; the production-only compliance scan separately confirms zero
  findings, warnings, and suppressions.
- Expected bad-fixture findings: AA001, AA002, AA003, AA004, AA006, two AA007 subchecks, AA010, and AA012 in `fixtures/bad_python/agent.py`. These are deliberate demo/golden defects; no action.
- Expected test sentinels: AA006 secret/PII literals in redaction, static-rule, HTML, and judgment tests. Values are synthetic and verify that raw sentinels never reach reports; no production credential or personal data is present.
- Action taken: AA004 now requires recognized `@function_tool` provenance instead of parameter-name heuristics, eliminating the previous scanner-internal false positives. AA001 exit/base-case evidence, AA003 side-effect evidence, AA011 eval evidence, and AA012 nearby-observability evidence were also tightened. Explicit GPT-5.6 output, timeout, retry, call-budget, storage, metadata, and logging controls remain in place.
- Final whole-repository count: 20 expected findings (9 deliberate bad-fixture findings
  and 11 synthetic test sentinels), zero production-code findings, and zero unexplained
  analysis warnings.

## Compatibility evidence

- Windows Python 3.13.7 clean clone: 158 tests PASS; acceptance, compliance, Ruff,
  strict mypy, and 86% branch coverage PASS. Node 24.14.1 site build and two rendered
  route tests PASS.
- Ubuntu/WSL Python 3.13.12 clean clone: 158 tests PASS; acceptance, compliance,
  Ruff, strict mypy, and 86% branch coverage PASS. Node 22.22.2 site build and two
  rendered route tests PASS.
- The repaired GitHub Actions workflow passed all nine Python 3.11-3.13 cells on
  Ubuntu, Windows, and macOS plus package/site, isolated wheel audit, and container
  lifecycle jobs in run `29703827878`.

## Phase 1 evidence

- Exact verified commit: `846c7f7` (`docs: prepare competition submission assets`).
- Windows clean clone: Python 3.13.7, Node 22.19.0; 158 tests, acceptance,
  compliance, Ruff, strict mypy over 29 files, 86% branch coverage, clean npm
  install, production build, and two rendered-route tests all PASS.
- Ubuntu/WSL clean clone: Python 3.13.12, Node 22.22.2; the same Python gates,
  coverage, clean npm install, build, and two rendered-route tests all PASS.
- The Windows npm install emitted one best-effort cleanup warning for a nested
  optional WASM directory but exited 0; the subsequent production build and route
  tests passed. Ubuntu installed cleanly.
- The exact demo sequence produced 10 deliberate fixture findings with three
  redactions, generated HTML/JSON, bound review decisions, generated the approved-only
  FIXPLAN, and passed compliance entirely offline.

## Phase 2 evidence

- Exact verified implementation commit: `0d07f71` (`feat(mcp): harden local and
  hosted controls`).
- Windows clean clone: Python 3.13.7, Node 24.14.1; 167 tests, acceptance,
  compliance, Ruff, strict mypy over 29 files, 87% branch coverage, clean npm
  install, production build, and two rendered-route tests all PASS.
- Ubuntu/WSL clean clone: Python 3.13.12, Node 22.22.2; the same required gates,
  clean npm install, production build, and two rendered-route tests all PASS.
- The offline demo dry-run produced the expected 10 deliberate fixture findings
  and three redactions; JSON, standalone HTML, review manifest, approved-only
  FIXPLAN, and production compliance artifacts were generated without paid calls.
- No remote, deployment, repository access, credential, publication, video, or
  submission action occurred during Phase 2.

## Phase 3 burn-in evidence

- Implementation commit `6fdb102` and Phase 3-only corrections `1e8dff2` and
  `790ef5d` were pushed under explicit operator approval.
- GitHub run `29703827878` at `790ef5d` completed successfully with all 12 jobs:
  the nine-cell Python 3.11-3.13 matrix on Ubuntu, Windows, and macOS; package,
  SBOM, SARIF, and site; isolated wheel dependency audit; and container health,
  unauthorized-MCP, and graceful-shutdown smoke checks.
- Each matrix cell passed 175 tests, offline acceptance, production compliance,
  Ruff, strict mypy, and 88% branch coverage. The run produced no CI annotations.
- A fresh Ubuntu/WSL clone at `790ef5d` passed the full §3 command set, site lint
  and `tsc --noEmit`, the offline demo sequence, and a clean-tree check. A fresh
  Windows clone passed clean npm install, lint, type check, production build, and
  both rendered-route tests; GitHub supplied the clean Windows Python gates.
- The repository remains private. No deployment, access change, publication,
  credential distribution, video upload, paid model call, or submission occurred.
- GitHub artifact attestation is skipped while the repository is private because
  the feature is unavailable for user-owned private repositories. RC artifacts and
  SBOMs remain retained; signed/attested publication is deferred to Phase 7.
