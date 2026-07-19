# Progress

## Current gate

Completion Plan v2 Phase 1 — rules compliance and submission assets for
`v1.0.0-rc2`.

## Status

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
- [ ] Operator captures the Codex Session ID outside the repository.
- [ ] Obtain operator approval before pushing Phase 1 commits or the RC2 tag.

## Notes

- Workspace began as an empty Git repository.
- One paid GPT-5.6 smoke request was explicitly authorized and completed successfully; no further paid requests are authorized.
- The static engine evaluates AA001/2/3/4/6/7/10/11/12 and records AA005/8/9 as judgment-only/not applicable during static scans.
- Semantic HTML, CSP, escaping, redaction, and standalone behavior pass automated tests; the user opened and approved the rendered final HTML report.
- Live evidence: `.archagent-audit/live-smoke.json` records one synthetic-code request to `gpt-5.6`, a completed structured result, one expected finding, and no analysis warnings. The evidence contains no API key or submitted code.

## Self-scan triage

Latest output: `.archagent-audit/self-scan.json` from the Phase 0 clean-clone
acceptance run (generated and gitignored).

- Coverage: 50/50 project Python files analyzed, 11 excluded-directory records, and
  zero analysis warnings. The production-only compliance scan separately confirms
  zero findings and zero suppressions.
- Expected bad-fixture findings: AA001, AA002, AA003, AA004, AA006, two AA007 subchecks, AA010, and AA012 in `fixtures/bad_python/agent.py`. These are deliberate demo/golden defects; no action.
- Expected test sentinels: AA006 secret/PII literals in redaction, static-rule, HTML, and judgment tests. Values are synthetic and verify that raw sentinels never reach reports; no production credential or personal data is present.
- Action taken: AA004 now requires recognized `@function_tool` provenance instead of parameter-name heuristics, eliminating the previous scanner-internal false positives. AA001 exit/base-case evidence, AA003 side-effect evidence, AA011 eval evidence, and AA012 nearby-observability evidence were also tightened. Explicit GPT-5.6 output, timeout, retry, call-budget, storage, metadata, and logging controls remain in place.
- Final whole-repository count: 20 expected findings (9 deliberate bad-fixture
  findings and 11 synthetic AA006 test sentinels), zero production-code findings,
  and zero unexplained analysis warnings.

## Compatibility evidence

- Windows Python 3.13.7 clean clone: 158 tests PASS; acceptance, compliance, Ruff,
  strict mypy, and 86% branch coverage PASS. Node 24.14.1 site build and two rendered
  route tests PASS.
- Ubuntu/WSL Python 3.13.12 clean clone: 158 tests PASS; acceptance, compliance,
  Ruff, strict mypy, and 86% branch coverage PASS. Node 22.22.2 site build and two
  rendered route tests PASS.
- The configured GitHub Actions matrix remains in burn-in: its first run proved the
  Docker build and six Python cells, but Python 3.11 dependency-audit isolation and
  the previously missing site plugin require the planned Phase 3 workflow repair.

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
