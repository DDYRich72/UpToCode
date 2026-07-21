# UpToCode — Implementation Specification

> Product name: **UpToCode**. Python package: `uptocode`. CLI: `uptocode`.
> PyPI availability was rechecked on 2026-07-20 and remained open; recheck immediately
> before publication because registry availability can change.

**Event:** OpenAI Build Week, Developer Tools track  
**Deadline:** Tuesday, July 21, 2026 at 5:00 PM PT  
**One-line description:** A design-time architecture-quality linter for Python and TypeScript agent applications that finds missing execution bounds, budgets, approvals, validation, evals, and observability before the application reaches production.

UpToCode is not positioned as the first or only agent-security scanner. Its wedge is architecture-quality review backed by explainable static evidence and optional GPT-5.6 judgment, followed by an approval-driven, Codex-ready remediation plan.

---

## 1. Product Contract

### Primary user

A developer or architect building Python agent applications with the OpenAI Agents SDK, LangGraph, or recognizable custom Python loops.

### MVP outcome

The user can scan a repository, understand every supported finding and every analysis gap,
approve selected findings, generate a non-mutating `FIXPLAN.md`, and explicitly ask an
external coding runner to remediate approved findings in isolated Git worktrees.

### MVP surfaces

- Terminal, JSON, and standalone HTML reports.
- Review manifest and generated remediation plan.
- MCP server exposing fast static checks to coding agents.
- Optional GPT-5.6 judgment tier using the Responses API and Pydantic Structured Outputs.

### Non-goals for v1

- No linting of `AGENTS.md`, `CLAUDE.md`, or other instruction files.
- No runtime tracing or production observability service.
- No in-process source-changing codemods, mutation of the invoking checkout, automatic
  commits, automatic merges, or automatic deletion of remediation work.
- No claim that unsupported code is clean.
- No public deployment, package publication, or paid integration without approval.
- TypeScript and GitHub Actions are stretch work, not committed MVP scope.

### Success criteria

- Supported bad Python fixtures produce the exact expected rule IDs and evidence.
- Supported clean Python fixtures produce no findings and no unexplained coverage gaps.
- Unsupported or inconclusive syntax produces analysis warnings and coverage metadata.
- Static scans make no network calls.
- Judgment runs only when both `--judgment` and `--send-code` are supplied.
- Secret values never appear in reports, logs, snapshots, or judgment payloads.
- Scan, review, planning, and `fix` dry-runs never modify scanned source files.
- `fix --apply` invokes an external runner only in retained isolated branches/worktrees.
- The active Definition of Done and validation report agree after any authorized cut.

---

## 2. Technical Architecture

```text
uptocode/
├── engine.py              # discover → parse → normalize → check → report
├── models.py              # Pydantic report, finding, coverage, and manifest models
├── config.py              # .uptocode.yml, ignore and suppression behavior
├── redaction.py           # secret detection and irreversible display redaction
├── adapters/
│   ├── python.py          # common AST utilities and custom-loop extraction
│   ├── openai_agents.py   # OpenAI Agents SDK evidence
│   └── langgraph.py       # LangGraph evidence
├── rules/
│   ├── registry.py        # rule dispatch and applicability
│   └── core.yml           # metadata, templates, citations, judgment prompts
├── judgment.py            # optional GPT-5.6 Responses API structured parsing
├── review.py              # approval/rejection manifest
├── planner.py             # approved findings → FIXPLAN.md
├── reporters/
│   ├── terminal.py
│   ├── json.py
│   ├── html.py
│   └── github.py          # stretch: workflow annotations and job summary
├── mcp_server.py
├── cli.py
└── tests/
```

### Stack decisions

- Python 3.11+ with a `pyproject.toml` package.
- `ast` for Python parsing; no source rewriting.
- Pydantic for public data contracts and GPT-5.6 Structured Outputs.
- Typer for the CLI and Rich for terminal review.
- PyYAML for the rulepack and configuration.
- Official Python MCP SDK with stdio transport.
- Pytest for all automated tests.

### Discovery and privacy defaults

- Honor `.gitignore` plus `.uptocode.yml` exclusions.
- Exclude `.git`, virtual environments, dependency directories, caches, build output, generated files, binary files, and files above the configured size limit.
- Default maximum source file size: 1 MiB. Default excerpt limit: 40 lines and 2,000 aggregate input tokens per judgment rule.
- Honor `# uptocode: ignore AA001` on the relevant statement and count suppressions in report metadata.
- Detect secrets before excerpt construction. Replace the secret value with `[REDACTED:<kind>]` everywhere outside the in-memory detector.
- Static scanning is the default and is offline. Judgment requires `--judgment --send-code`; `--judgment` without `--send-code` is a configuration error with exit code 2.

### Normalized evidence model

Adapters emit facts with source locations and provenance, not bare booleans:

```json
{
  "loops": [{
    "file": "src/agent.py",
    "line": 42,
    "framework": "openai-agents",
    "bound_kind": "sdk-default|explicit|disabled|custom|unknown",
    "max_turns": 10,
    "has_wall_clock_deadline": false
  }],
  "tools": [{
    "name": "delete_user",
    "file": "src/tools.py",
    "line": 12,
    "side_effect": "destructive|write|read|unknown",
    "approval_evidence": [],
    "argument_validation_evidence": []
  }],
  "model_calls": [{
    "file": "src/agent.py",
    "line": 25,
    "output_token_limit": null,
    "run_budget_evidence": [],
    "timeout_evidence": [],
    "retry_evidence": [],
    "retry_safe": "yes|no|unknown"
  }],
  "external_flows": [{
    "source": "http|file|email|user|unknown",
    "sink": "prompt|tool|unknown",
    "demarcation_evidence": []
  }],
  "orchestration": {"agent_count": 1, "pattern": "single|handoff|graph|manager|unknown"},
  "eval_artifacts": [],
  "observability_evidence": [],
  "analysis_warnings": []
}
```

Each adapter records which constructs it recognizes. An unrecognized or inconclusive construct creates an `analysis_warning`; it cannot satisfy a rule and cannot justify a finding.

---

## 3. Public Data Contracts

### Finding

```json
{
  "rule_id": "AA001",
  "severity": "critical|warning|info",
  "tier": "static|judgment",
  "maturity": "stable|experimental",
  "title": "Unbounded agent loop",
  "file": "src/agent.py",
  "line": 42,
  "evidence": [{"kind": "explicit-disabled-limit", "detail": "max_turns=None"}],
  "verdict": {
    "observed": "Runner.run explicitly disables its turn limit.",
    "implies": "A failed tool interaction can continue without a turn ceiling.",
    "recommended": "Set an explicit turn cap and handle MaxTurnsExceeded.",
    "tradeoff": "A cap can truncate long tasks, so preserve partial results."
  },
  "citations": [{"publisher": "OpenAI", "title": "Runner reference", "url": "https://openai.github.io/openai-agents-python/ref/run/", "status": "normative|supporting"}],
  "excerpt": "result = await Runner.run(agent, task, max_turns=None)",
  "context": {"function": "run", "framework": "openai-agents"},
  "remediation": {
    "complexity": "trivial|moderate|complex",
    "status": "proposed|approved|rejected|planned",
    "plan": null
  }
}
```

Findings are deterministically ordered by severity, normalized path, line, and rule ID. Paths use `/` separators and are relative to the scan root.

### Report envelope

```json
{
  "schema_version": "2.2",
  "tool_version": "1.7.0",
  "scan_root": ".",
  "generated_at": "RFC3339 timestamp",
  "findings": [],
  "coverage": {
    "files_discovered": 0,
    "files_analyzed": 0,
    "files_skipped": 0,
    "frameworks_detected": [],
    "rules_evaluated": [],
    "experimental_rules_evaluated": [],
    "rules_not_applicable": [],
    "language_coverage": []
  },
  "analysis_warnings": [],
  "judgment_status": "not-requested|completed|partial|failed",
  "redactions": {"secrets": 0, "pii": 0},
  "suppressions": 0,
  "suppression_details": [],
  "baseline_debt": {"new": [], "aging": [], "resolved": []}
}
```

Report 2.2 adds strict per-language coverage while preserving aggregate coverage fields.
Report citations serialize `publisher`, `title`, `url`, and `status`; readers accept
the legacy 2.0 `vendor` key. Registry maturity defaults to `stable`. Experimental findings
remain visible but do not participate in `--fail-on` unless `--include-experimental` is set.

Baseline 2.1 stores `entries` containing `fingerprint`, `rule_id`, `file`, and `first_seen`.
The loader upgrades 2.0 bare-fingerprint baselines in memory using the baseline creation
time as `first_seen`. Applying a baseline classifies new, aging, and resolved debt before
aging findings are muted; updating preserves `first_seen` for persisting fingerprints.

Suppressions accept `# uptocode: ignore AA001` or `// uptocode: ignore AA001` plus optional `owner=NAME`, quoted
`reason="TEXT"`, and `expires=YYYY-MM-DD`. An expiry equal to the scan date remains active;
an earlier date emits `SUPPRESSION_EXPIRED` and does not suppress. Malformed metadata acts
as a bare suppression and emits `SUPPRESSION_METADATA_INVALID`.

### Review manifest

The manifest stores the report fingerprint, finding fingerprints, `approved|rejected` decisions, timestamp, and optional reviewer note. Planning refuses a manifest from a different report.

---

## 4. Core Rulepack

| ID | Rule | Tier | Severity | Required positive evidence |
|---|---|---|---|---|
| AA001 | Unbounded agent loop | Static | critical | Explicitly disabled SDK/framework limit, or demonstrably unbounded custom loop. Omitted OpenAI `Runner.run(max_turns=...)` is clean because the SDK default is bounded. |
| AA002 | Missing whole-run budget | Static | critical | Agent loop/model-call path with neither enforced run budget nor output-token ceiling. Report the two missing controls separately; an output cap is not a spend budget. |
| AA003 | Ungated destructive action | Static + judgment | critical | Destructive/write tool plus no recognized approval mechanism. Judgment may classify only ambiguous side effects. |
| AA004 | Unvalidated tool arguments | Static | critical | Model-controlled value reaches SQL, shell, filesystem, or HTTP sink without recognized validation or parameterization. |
| AA005 | Untrusted content enters prompt raw | Judgment | critical | Proven external-source-to-prompt flow with no demarcation/sanitization evidence; judgment confirms exploitability. |
| AA006 | Secret or PII exposure | Static | critical | Secret literal or secret-derived value reaches prompt/log. Finding excerpts must redact the value. Environment lookup alone is not a finding. |
| AA007 | Missing resilience controls | Static | warning | Emit distinct evidence for missing timeout and missing retry/backoff. Do not recommend retries when replay safety is `no` or `unknown`. |
| AA008 | Unjustified orchestration complexity | Judgment | warning | More than one agent plus concrete orchestration evidence; judgment compares role separation/parallelism with a simpler single-agent design. |
| AA009 | Poor tool schema | Judgment | warning | Tool definition exists and judgment evaluates name, description, parameter documentation, constraints, and overlap. |
| AA010 | Unvalidated model output before side effect | Static + judgment | warning | Model output reaches a write/destructive sink without schema or domain validation. |
| AA011 | No agent eval coverage | Static + judgment | warning | Supported agent entrypoints exist but no tests/evals exercise them. Judgment proposes three repo-specific cases. |
| AA012 | No agent observability | Static | info | Supported agent loop/tool execution exists without recognized logging or tracing around decisions and tool calls. |
| AA013 | Unbounded context growth | Static | warning | In one recognized loop, a proven list is appended and passed as `messages`, `input`, or `history` to a recognized model call, with no recognized truncation in the loop or containing function. Incomplete recognition produces an analysis warning. |

### Rule behavior constraints

- One finding represents one location and one actionable defect. AA007 may emit separate timeout, retry, and retry-without-backoff findings at the same call site.
- Static findings require source-backed evidence. Names alone may select candidates but do not prove a verdict.
- Judgment cannot upgrade unsupported syntax into a static fact; it operates only on normalized evidence and redacted excerpts.
- Every rule entry contains applicability, evidence requirements, severity, maturity, verdict templates, suppressions, and structured public citations. The registry is the citation source of truth for static and judgment findings.
- Use at least two applicable primary-vendor sources when claiming vendor convergence. Otherwise state only the individual sourced recommendation.

### Citation registry

- OpenAI, *A practical guide to building agents*: https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf
- OpenAI Agents SDK, runner limits: https://openai.github.io/openai-agents-python/ref/run/
- OpenAI Agents SDK, human approval: https://openai.github.io/openai-agents-python/human_in_the_loop/
- OpenAI, safety in building agents: https://developers.openai.com/api/docs/guides/agent-builder-safety
- OpenAI, function calling and strict schemas: https://developers.openai.com/api/docs/guides/function-calling
- OpenAI, working with evals: https://developers.openai.com/api/docs/guides/evals
- OpenAI Agents SDK, tracing: https://openai.github.io/openai-agents-python/tracing/
- Anthropic, building effective agents: https://www.anthropic.com/engineering/building-effective-agents
- Anthropic, defining tools: https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools
- Anthropic, mitigating prompt injection: https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/mitigate-jailbreaks
- Google ADK, evaluating agents: https://adk.dev/evaluate/

---

## 5. Judgment Tier

- Model: `gpt-5.6` through `client.responses.parse(...)`.
- Output contract: a Pydantic model containing a list of candidate findings with the four verdict fields and a citation selected from the rule entry.
- Batch once per judgment rule, not once per candidate.
- Send only normalized evidence and redacted, bounded excerpts.
- Do not set unsupported sampling parameters. Use an explicit reasoning effort only after a smoke test establishes the desired cost/latency tradeoff.
- Handle schema-valid success, model refusal, timeout, authentication failure, and other API errors separately.
- On judgment failure, preserve all static findings, set `judgment_status` to `partial` or `failed`, add an analysis warning, and never fabricate an `info` finding from raw model text.
- All automated tests use mocks and make no network calls. One live smoke test is run only with an API key and explicit cost authorization.

---

## 6. User Interfaces

### CLI

```text
uptocode scan PATH [--format terminal|json|html|github] [--output FILE]
                        [--judgment --send-code]
                        [--fail-on critical|warning|info]
                        [--include-experimental] [--share-safe]
uptocode review REPORT [--approve IDS|--approve-all] [--reject IDS]
                            [--non-interactive]
uptocode plan REPORT --manifest MANIFEST [--output FIXPLAN.md]
uptocode fix REPORT --manifest MANIFEST --runner codex|command
                    [--command TEMPLATE] [--verify-command COMMAND] [--apply]
uptocode serve
```

- `scan` defaults to terminal format and static-only behavior.
- `--share-safe` is valid for JSON, HTML, and SARIF only. It replaces `scan_root` with `<scan-root>`, retains `metadata.repository_revision`, and removes absolute Windows, UNC, Linux-home, macOS-home, and scan-root paths from every serialized string.
- `--output` is required for HTML and optional for JSON/GitHub; without it, machine-readable output goes to stdout and diagnostics go to stderr.
- Exit 0: no finding reaches the configured threshold. Exit 1: threshold breached. Exit 2: invalid configuration or unrecoverable scan error.
- File parse failures are recoverable analysis warnings unless no supported file can be analyzed.
- `review` consumes an existing JSON report and never rescans implicitly.
- `plan` includes only approved findings from a matching manifest and never edits scanned files.
- `fix` includes only approved findings from a matching manifest and defaults to a
  no-write dry-run. `--apply` requires a clean Git checkout and confines each external
  runner invocation to a retained `uptocode/fix-<fingerprint12>` branch/worktree.

### HTML

- One self-contained file with inline CSS and JavaScript.
- Header shows repository, coverage, judgment status, redaction count, and counts by severity.
- Use a bar chart labeled **Findings by category**; do not invent a quality score.
- Findings are grouped by severity and show evidence, verdict, citations, redacted excerpt, and remediation complexity.
- HTML is read-only in v1.

### GitHub output — stretch

- Emit workflow annotations and append a Markdown summary to `$GITHUB_STEP_SUMMARY`.
- Do not promise a PR comment without a separate authenticated GitHub API integration.

### MCP server

- `audit_file(path, judgment=false, send_code=false)`
- `audit_diff(diff, judgment=false, send_code=false)`
- `check_tool_schema(schema_json, judgment=false, send_code=false)`
- `check_loop(snippet)`
- `get_rule(rule_id)`

Static-only is the default. Judgment requires both flags and uses the same redaction and payload limits as the CLI. Malformed arguments return structured errors without terminating the stdio server.

---

## 7. Review and Remediation

Flow: `scan → review → plan → optional fix --apply`.

1. Scan writes a versioned JSON report.
2. Review records explicit approval/rejection decisions in `.uptocode/manifest.json` or a requested path.
3. Plan verifies report/manifest fingerprints and writes `FIXPLAN.md` for approved findings.
4. Each plan entry contains finding ID/fingerprint, objective, evidence, files likely affected, ordered steps, acceptance checks, risks/tradeoffs, and a copy-paste Codex prompt.
5. `fix` previews its branches, runner argv, and verification steps without writing by
   default. With `--apply`, it invokes the selected external runner in one retained
   isolated branch/worktree per approved finding, rescans for fingerprint absence, and
   optionally runs a caller-supplied verification command.
6. UpToCode never edits source directly, changes the invoking checkout, commits, merges,
   or deletes remediation work.

---

## 8. Delivery Gates and Cut Policy

### Gate 1 — Scaffold and vertical slice

Package, config, public schemas, discovery, redaction, CLI shell, AA001 vertical slice, deterministic JSON, and tests.

### Gate 2 — Python static engine

All static portions of AA001–AA013, Python adapters, bad/clean fixtures, suppressions, coverage metadata, exit codes, and goldens.

### Gate 3 — Judgment and developer surfaces

GPT-5.6 structured judgment, review manifest, FIXPLAN generation, standalone HTML, and MCP integration.

### Gate 4 — Submission

README, self-scan triage, authorized live smoke test, demo recording, Devpost assets, and final validation report. TypeScript and GitHub Actions may be attempted only after Gate 3 passes.

### Monday noon cut policy

If Gate 3 has not passed by Monday at 12:00 PM PT, do not begin stretch work. If any already-started stretch item is incomplete, cut in this order: TypeScript adapter, GitHub Actions, judgment-enabled MCP calls. Static MCP tools remain committed. Every cut must update `PROGRESS.md`, the active Definition of Done, README claims, demo script, and validation report in the same commit.

Never cut: Python static engine, at least two judgment rules, review manifest, FIXPLAN generation, standalone HTML, static `check_loop`, privacy/redaction controls, tests, or demo.

---

## 9. Test and Acceptance Requirements

### Rule tests

- AA001: default `Runner.run(...)` clean; explicit `max_turns=10` clean; `max_turns=None` finding; bounded and unbounded custom loops distinguished; suppression honored.
- Every rule: positive case, clean case, suppression case, unsupported-syntax case, and false-positive regression.
- AA006: detected values are absent from terminal, JSON, HTML, logs, snapshots, and judgment payloads.
- AA007: timeout and retry evidence are independent; retry recommendations are withheld for unsafe/unknown replay.
- AA007: proven retries without Tenacity exponential waits, exponential/multiplied sleep, or OpenAI built-in `max_retries` backoff emit a distinct warning.
- AA013: cover positive, every recognized truncation, suppression, inconclusive syntax, alias/name false positives, and nested lexical scopes.

### Pipeline tests

- Deterministic ordering, normalized paths, schema validation, stable goldens, and exit codes 0/1/2.
- Empty directory, no-agent repository, parse failure, mixed supported/unsupported files, excludes, and size limits.
- Structured judgment success, refusal, timeout, authentication failure, and partial failure; static findings always survive.
- Review and planning use temporary fixture copies and leave canonical fixtures and the git worktree unchanged.
- Standalone HTML renders without a server and displays coverage, warnings, redactions, bar chart, and findings.
- Baseline tests cover introduce/persist/resolve, stable `first_seen`, 2.0 loading, and combined apply/update behavior. Suppression tests cover bare/full/malformed metadata and yesterday/today/tomorrow. Share-safe tests render JSON, HTML, and SARIF from hostile absolute paths.
- MCP survives malformed arguments; static-only default makes no network calls; `check_loop` and `audit_diff` detect AA001.

### Definition of Done

- All active gate criteria pass and are recorded in `tasks/validation-report.md`.
- Full offline suite passes.
- Bad/clean fixture expectations pass without modifying canonical fixtures.
- HTML has been opened and visually inspected.
- MCP integration tests pass.
- Self-scan findings and analysis gaps are triaged.
- One authorized live GPT-5.6 smoke test passes before submission.
- README and demo claims match the shipped surface exactly.
- Public repo/private sharing, video, submission, package publication, and any other external action occur only after explicit approval.

---

## 10. Demo Outline — Under Three Minutes

1. Problem and positioning: architecture-quality failures remain easy to ship even when code is syntactically valid.
2. Scan a deliberately bad Python fixture; show terminal output and coverage-aware HTML.
3. Explain one deterministic finding and one GPT-5.6 judgment finding, including direct citations and redaction.
4. Approve selected findings and generate `FIXPLAN.md`; preview `uptocode fix` and explain
   that mutation requires explicit `--apply` and occurs only through an external runner in
   an isolated worktree.
5. Show a coding agent calling MCP `check_loop` before writing an explicitly unbounded loop.
6. Close with rulepack extensibility, Codex build evidence, and the authorized GPT-5.6 judgment path.
