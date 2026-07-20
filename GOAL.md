# /goal — Build UpToCode with gated TDD

Build UpToCode end to end in this repository. `SPEC.md` defines **what** to build; this prompt defines **how** to work. If they conflict, `SPEC.md` wins on product behavior and this prompt wins on process. Do not silently resolve a material conflict: record it in `DECISIONS.md`, choose the smallest behavior that satisfies the spec, and continue only when the choice does not change scope, cost, security, privacy, deployment, or public interfaces.

The current layer is implementation and local verification. Do not publish, deploy, submit, send external messages, or use paid APIs without explicit approval.

---

## 1. Operating Contract

Work autonomously through the active gates using test-driven development. The spec is the control surface; do not add features because they seem useful.

For each task:

1. Read `SPEC.md`, `PROGRESS.md`, and the current task in `tasks/implementation-plan.md`.
2. Select the highest-priority incomplete item in the active gate.
3. **RED:** write the smallest failing test that expresses the acceptance behavior. Run it and confirm it fails for the intended reason.
4. **GREEN:** implement the minimum behavior that passes the targeted test.
5. **REFACTOR:** improve structure without broadening behavior.
6. Run the targeted tests, then the full offline suite.
7. Update `PROGRESS.md` and `tasks/validation-report.md` with commands and evidence.
8. Commit the test and implementation together with an atomic message such as `feat(AA001): detect explicitly disabled turn limit`.
9. Repeat until the gate passes or a stop condition applies.

Never delete, skip, or weaken a correct test to make the suite pass. If a test expectation is wrong, explain why in `DECISIONS.md`, correct it, and name that correction in the commit message.

---

## 2. Bootstrap Before Product Code

Inspect the repository first. Reuse existing equivalents when present; otherwise create:

```text
docs/constitution.md
docs/architecture.md
docs/roadmap.md
specs/001-mvp-scope.md
tasks/implementation-plan.md
tasks/validation-report.md
PROGRESS.md
DECISIONS.md
BLOCKED.md
```

Populate them from `SPEC.md`; do not invent a second scope. `tasks/implementation-plan.md` must map every active Definition of Done criterion to implementation and test work. `tasks/validation-report.md` starts with every criterion marked `NOT RUN`.

Then scaffold a Python 3.11+ package named `uptocode` with the canonical `uptocode` CLI
entry point, `pyproject.toml`, tests, and the directory structure in `SPEC.md`. Pin direct
dependencies to compatible version ranges and record the resolved environment in the
validation report.

The bootstrap itself requires a green packaging/import smoke test before Gate 1 product work begins.

---

## 3. Hard Rules

- Static scans and all ordinary tests make no network calls.
- Judgment tests use recorded or mocked Responses API results. Permit exactly one separately marked live smoke test.
- Do not run the live test without `OPENAI_API_KEY` and explicit user authorization for paid API use.
- Never include raw detected secrets in exceptions, logs, reports, snapshots, test failure output, or model payloads.
- Never treat unsupported or inconclusive syntax as clean. Emit coverage metadata and analysis warnings.
- Never infer a static verdict from a suspicious function name alone; require the positive evidence defined in `SPEC.md`.
- Never set GPT-5.6 sampling or reasoning parameters without verifying that the current API supports them and recording the rationale.
- Never mutate the scanned source tree. v1 remediation ends at a generated plan.
- Never update golden files as a side effect of a normal test. A deliberate regeneration command must show the diff and be committed separately with an explanation.
- Keep adapters framework-specific behind the normalized evidence contract. Do not create a second rule engine per framework.
- Prefer small, cohesive functions and modules. Refactor when complexity obscures evidence provenance; do not chase an arbitrary line count.
- Preserve deterministic ordering and normalized relative paths in every machine-readable result.
- Do not change the active stack, scope, privacy model, public CLI, report schema, or rule semantics without updating `SPEC.md` and recording the decision.

---

## 4. Gate 1 — Scaffold and AA001 Vertical Slice

Implement:

- Package and CLI scaffold.
- `.uptocode.yml` loading, default exclusions, `.gitignore` handling, and source discovery.
- Pydantic models for findings, report envelope, coverage, warnings, redactions, and review manifest.
- Secret redaction boundary used by all output paths.
- Python AST adapter skeleton and normalized evidence model.
- AA001 for OpenAI Agents SDK and recognizable custom Python loops.
- Deterministic JSON reporter.
- `scan` command with exit codes 0, 1, and 2.

Required AA001 tests:

- `Runner.run(agent, task)` is clean because the SDK default is bounded.
- `Runner.run(agent, task, max_turns=10)` is clean.
- `Runner.run(agent, task, max_turns=None)` reports AA001.
- A bounded custom loop with an effective counter/break is clean.
- A demonstrably unbounded custom loop reports AA001.
- Unknown dynamic configuration produces an analysis warning, not a finding.
- `# uptocode: ignore AA001` suppresses the finding and increments the suppression count.

### Gate 1 pass condition

- Bootstrap/import smoke test passes.
- AA001 matrix passes.
- Report JSON validates against the Pydantic contract.
- Two identical scans, after removing volatile timestamp fields, produce identical output.
- Threshold exit-code tests pass.
- Full offline suite is green.

Do not begin Gate 2 until every condition is recorded `PASS` in `tasks/validation-report.md`.

---

## 5. Gate 2 — Python Static Engine

Implement the static portions of AA001–AA012, one rule at a time. For each rule, add before implementation:

- A positive fixture and expected evidence.
- A clean counterpart.
- A suppression case.
- An unsupported or inconclusive case that yields an analysis warning.
- A false-positive regression case.

Build:

- OpenAI Agents SDK adapter.
- LangGraph adapter.
- Recognizable custom Python loop and raw OpenAI call extraction.
- Rule registry and YAML metadata/citation loader.
- Terminal reporter.
- Coverage, warning, suppression, exclusion, and redaction accounting.
- Golden fixtures under `fixtures/bad_python` and `fixtures/clean_python`.

### Required edge cases

#### AA001 — execution bounds

- SDK default, explicit numeric bound, explicit `None`, config variable with known constant, unknown dynamic value, LangGraph supported limit placement, recursion, nested function, and async loop.

#### AA002 — budgets

- Output-token cap only, whole-run budget only, both controls, neither control, and a token counter that is observed but not enforced. Findings must state which control is missing.

#### AA003 — approvals

- OpenAI `needs_approval=True`, callable approval, known destructive tool with no gate, write tool with no gate, read-only tool, and ambiguous side effects. Ambiguous cases remain judgment candidates rather than static critical findings.

#### AA004 — argument validation

- SQL interpolation versus parameters, shell argument versus allowlist, unresolved filesystem path versus resolved-prefix check, and unrestricted URL versus validated scheme/host.

#### AA006 — secrets

- Literal API key, environment lookup alone, secret-derived prompt interpolation, suppression, and multiple reporters. Assert the sentinel secret value never appears anywhere observable.

#### AA007 — resilience

- Missing timeout, recognized call-level timeout, recognized client-level timeout, missing retry, retry with bounded backoff, retry without backoff, and non-idempotent/unknown replay safety. Timeout and retry defects are independently addressable.

#### AA010–AA012

- Validated versus raw model output before a side effect, tests/evals that actually exercise an agent entrypoint, and logging/tracing around both loop decisions and tool execution.

### Gate 2 pass condition

- Bad fixture emits the exact active static finding fingerprints.
- Clean fixture emits zero findings and zero unexplained analysis warnings.
- Empty/no-agent repositories exit 0 with truthful coverage.
- Parse failures warn and continue; a repository with no analyzable supported file exits 2.
- Terminal and JSON output contain no raw test secret.
- Excludes, size limits, suppressions, path normalization, deterministic ordering, and exit codes pass.
- Full offline suite is green.

---

## 6. Gate 3 — Judgment, Review, HTML, and MCP

### Judgment

Implement GPT-5.6 through `client.responses.parse(model="gpt-5.6", ..., text_format=<PydanticModel>)`.

- Batch candidates once per judgment rule.
- Send only normalized evidence and redacted, bounded excerpts.
- Require both `--judgment` and `--send-code`.
- Keep static results when judgment refuses, times out, lacks credentials, or fails.
- Record `completed`, `partial`, or `failed`; add an analysis warning rather than converting raw text into a finding.

Test with mocks:

- Structured success.
- Model refusal.
- Timeout.
- Authentication failure.
- One rule failing while others succeed.
- Missing `--send-code` returning exit 2 before any client call.
- Payload redaction and token/excerpt bounds.

### Review and planning

- `review` consumes a JSON report and writes decisions keyed by report and finding fingerprints.
- `plan` rejects a mismatched manifest and includes only approved findings.
- Generated entries contain objective, evidence, likely files, ordered steps, acceptance checks, risks/tradeoffs, and a Codex-ready prompt.
- Neither command rescans or changes scanned source.

### HTML

Generate a self-contained report with coverage, warnings, judgment status, redaction count, severity counts, a bar chart labeled `Findings by category`, and full finding cards. Do not present a synthetic quality score.

### MCP

Expose the five tools from `SPEC.md` over stdio. Static-only is the default. Invalid arguments return structured errors and the server remains alive.

### Gate 3 pass condition

- Mocked judgment matrix passes with no network calls.
- Review and planning tests operate on temporary copies and leave canonical fixtures and git status unchanged.
- HTML golden/semantic checks pass and a rendered report is visually inspected.
- MCP process integration test passes.
- `check_loop` and `audit_diff` detect AA001.
- Malformed MCP calls do not terminate the server.
- Full offline suite is green.

---

## 7. Gate 4 — Submission and Stretch Work

First complete committed submission work:

- README with positioning, supported/unsupported constructs, install, CLI, privacy behavior, rule table, direct citations, MCP registration, limitations, and sample output.
- Self-scan with every finding and analysis warning triaged in `PROGRESS.md`.
- Cross-platform acceptance runner at `scripts/acceptance.py`.
- Demo fixtures and the under-three-minute demo sequence from `SPEC.md`.
- One authorized live GPT-5.6 smoke test, with request count and result recorded but no sensitive payload retained.
- Final `tasks/validation-report.md` mapping every active Definition of Done criterion to evidence.

Only after Gate 3 passes may stretch work begin:

1. TypeScript adapter and bad/clean TypeScript fixtures.
2. GitHub Actions wrapper that emits workflow annotations and `$GITHUB_STEP_SUMMARY`.
3. Judgment-enabled MCP calls.

Stretch work is not allowed to destabilize the committed MVP.

### Gate 4 pass condition

- `python scripts/acceptance.py` exits 0 on Windows and POSIX-compatible environments.
- Full offline suite passes from a clean checkout.
- Standalone HTML has been visually inspected.
- MCP integration passes.
- Self-scan is triaged.
- Authorized live smoke test passes.
- README and demo claims exactly match the active shipped scope.
- No external submission or publication has occurred without approval.

---

## 8. Cross-Platform Acceptance Runner

Implement `scripts/acceptance.py` using Python standard-library subprocess, tempfile, pathlib, json, and shutil APIs. It must:

1. Run the full offline pytest suite.
2. Scan `fixtures/bad_python` to JSON and compare sorted finding fingerprints with the checked-in golden.
3. Scan `fixtures/clean_python` and assert zero findings and zero unexplained analysis warnings.
4. Assert `--fail-on critical` returns 1 for the bad fixture and 0 for the clean fixture.
5. Copy the bad fixture and report into a temporary directory.
6. Run non-interactive review against the copied report and generate a plan from the resulting manifest.
7. Assert the plan contains only approved findings and that neither the copied source nor canonical fixtures changed.
8. Generate HTML in the temporary directory and assert required semantic markers are present.
9. Spawn the MCP server, call `check_loop`, verify AA001, send malformed arguments, and verify the server handles a subsequent valid request.
10. Run a static self-scan and store the output path in the validation report.
11. Compare git status before and after; fail if tracked files changed.

Do not depend on Bash, `jq`, `grep`, process substitution, or shell-specific redirection.

---

## 9. Time-Based Cut Policy

At Monday 12:00 PM PT:

- If Gate 3 is incomplete, do not start stretch work.
- If a stretch item was started and is incomplete, cut in this order: TypeScript, GitHub Actions, judgment-enabled MCP calls.
- Keep static MCP tools.

For every cut, update in the same commit:

- `SPEC.md` if necessary.
- `PROGRESS.md`.
- Active Definition of Done in `tasks/implementation-plan.md`.
- `tasks/validation-report.md`.
- README and demo claims.

Never cut the Python static engine, at least two judgment rules, review manifest, FIXPLAN generation, HTML, static `check_loop`, privacy/redaction controls, tests, or demo.

---

## 10. Stuck Protocol

After three materially different approaches or roughly 30 focused minutes on one task:

1. Add a `BLOCKED.md` entry with the task, evidence, approaches tried, current hypothesis, and smallest next experiment.
2. Mark the task blocked in `PROGRESS.md`.
3. Move to another task that does not depend on it.
4. Revisit blocked work before closing the active gate.

Do not mark a gate passed while one of its required criteria is blocked. If the same gate blocker remains after one hour, apply only an already-authorized cut. Otherwise stop and request direction.

---

## 11. Mandatory Approval Stops

Stop and request approval before:

- Running the live GPT-5.6 smoke test or otherwise incurring API cost.
- Sending private or customer source code to any external API.
- Publishing a package, repository, release, video, or Devpost submission.
- Deploying anything publicly.
- Sending comments, emails, or messages externally.
- Adding a paid service.
- Changing the privacy, authentication, or security model.
- Performing a destructive migration or deleting user/customer data.
- Changing committed MVP scope outside the pre-authorized cut policy.

Missing credentials are not permission to invent, expose, or bypass them. Complete offline work, document the exact blocked verification, and request the smallest required action.

---

## 12. Completion Report

Do not claim completion because code exists. Completion requires the active Definition of Done to be fully verified.

The final report must provide:

- Shipped committed scope and any stretch scope.
- Test/build/acceptance commands with pass/fail evidence.
- Rule coverage and known unsupported constructs.
- Judgment verification, including whether the authorized live smoke test ran.
- Privacy/redaction verification.
- Rendered HTML and MCP verification.
- Self-scan triage summary.
- Cuts, deviations, and unresolved blockers.
- External actions still awaiting approval.

Begin by inspecting the repository, materializing the durable project documents from `SPEC.md`, and running the bootstrap/import smoke test. Then enter Gate 1 at RED.

