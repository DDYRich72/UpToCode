# Batch 3 — Differentiation (`uptocode fix`, MCP-server rules, thin VS Code extension)

> Audience: Codex. Ground rules: `tasks/completion-plan-v2.md` §6; rule checklist: `tasks/batch-1-quick-wins.md` §1.1.
> **Prerequisite: Batches 1–2 landed** (stable fingerprints in baselines proven, adapters stable — `fix` verifies by re-scan, so the scanner underneath must be settled).
> Lanes: 3.1 and 3.3 are disjoint and parallel; 3.2 shares the rules lane with nothing else in this batch.

## 3.1 `uptocode fix` — close the remediation loop (~1–2 weeks)

Today the product ends at `FIXPLAN.md` + copy-paste. Add a command that drives an external coding agent per **approved** finding and verifies the result — converting plans into evidence-backed remediation.

### Contract (this changes the product's non-mutation story — handle deliberately)

- Default is **dry-run**: `uptocode fix REPORT --manifest MANIFEST` prints, per approved finding, the branch it would create, the runner invocation, and the verification steps. Nothing is executed or written.
- `--apply` is the only mutating path, and mutations happen **only on isolated branches** (`uptocode/fix-<fingerprint12>`), **only via the external runner**, never on the invoking branch. `fix` itself never edits source files.
- ⛔ Before implementation: update `SPEC.md`/README wording from "never mutates" to "mutates only via explicit `fix --apply`, on isolated branches, through an external runner" and get operator acknowledgment — GOAL.md §11 treats scope/contract changes as approval stops. Record in `DECISIONS.md`.

### Behavior under `--apply`, per approved finding

1. Require a clean worktree; refuse otherwise (exit 2).
2. Create the branch from the current HEAD.
3. Invoke the runner with the finding's FIXPLAN entry as the prompt:
   - `--runner codex` → the Codex CLI's non-interactive exec form (verify the exact current invocation at implementation time; do not guess flags).
   - `--runner command --command "TEMPLATE"` → placeholders `{prompt_file}`, `{file}`, `{rule_id}`, `{fingerprint}` for any agent CLI.
4. Verify: re-scan the target (the finding's stable fingerprint must be **absent**); run `--verify-command CMD` if supplied (e.g. the project's test suite) and require exit 0.
5. Success → leave the branch with the runner's changes and record PASS; failure → leave the branch for inspection, restore the original checkout, record FAIL with the reason. Never delete work; never auto-merge.
6. End with a summary table (terminal) + `fix-session.json` (strict model): per finding — branch, runner exit, fingerprint-gone, verify-command result.

### Tests (all offline — no live agent or model calls, ever, in CI)

Fake runner fixture: a script that applies a known patch (and a failing variant that doesn't). Git fixture repo under `tmp_path`. Assert: dry-run mutates nothing; branch isolation; fingerprint-absence gating (a runner that "fixes" the wrong thing → FAIL); dirty-worktree refusal; `--verify-command` failure → FAIL with branch retained; summary JSON matches the model. Windows + POSIX.

## 3.2 MCP-server audit rules (~1 week)

Nobody scans MCP servers for architecture quality; UpToCode ships a reference-grade one and is uniquely credible. Three conservative rules (IDs continue after Batch 1's AA013; follow the §1.1 checklist end to end):

- **AA014 — Network MCP transport without authentication evidence** (critical): FastMCP/low-level server run with `transport="streamable-http"`/`"sse"` (or the app mounted into uvicorn/Starlette) with no recognized auth boundary (auth middleware wrapper, bearer verification) in the same module/composition. stdio transport is clean by definition.
- **AA015 — Tools without annotations** (warning): tool registration (`add_tool`/`@server.tool`) with no `ToolAnnotations` supplied.
- **AA016 — Tool argument models accept unknown fields** (warning): no recognized strictness evidence (`extra="forbid"` on argument models, or an explicit strict-schema hardening step) for registered tools.

Evidence-first per the constitution: recognized SDK constructs only; anything else → coverage warnings. Fixtures: distill minimal bad/clean MCP-server patterns into `fixtures/bad_mcp_server` / `fixtures/clean_mcp_server` (model the clean one on `uptocode/mcp_server.py`'s own hardening). The self-scan (`scripts/compliance.py`) must remain zero-findings — if a new rule fires on UpToCode itself, fix UpToCode or the rule, never suppress silently.

### 3.2b Guide-derived control rules (launch as `experimental` via Batch 1's maturity tier)

Two further rules from the 2026-07-20 reference review (requirements discovered internally; **cite only public sources** per `DECISIONS.md` D011 — Anthropic tool-error-handling docs, MCP tools specification, NIST AI 600-1, OWASP agentic guidance):

- **AA017 — Undifferentiated tool errors** (warning, static + judgment): tool implementations whose exception handling returns one generic failure message with no recognized structure distinguishing transient / validation / permission / business failures, and no retryable signal (MCP servers: no `isError`-with-category pattern). Generic errors force agents into blind retries; both Anthropic and MCP docs specify structured error signaling. Static slice: except-blocks in recognized tools returning bare strings/generic messages; everything semantic → judgment candidates.
- **AA018 — Prompt-only policy enforcement** (warning, static + judgment): a recognized critical ordering or policy constraint (identity check before financial action, approval before destructive tool) that exists **only as prompt text**, with no programmatic evidence — no hook (`PreToolUse`-style interception), no prerequisite gate in the tool body, no tool_choice forcing. Vendor guidance is explicit that prompt instructions alone have a non-zero failure rate where deterministic compliance is required. This extends AA003's evidence model rather than duplicating it: AA003 asks "is there an approval gate"; AA018 asks "is the stated policy enforced anywhere but the prompt".

Escalation/handoff quality and provenance/temporal-integrity controls from the same review are **judgment-tier-only** concerns (semantic, weak static evidence); hold them for a Batch 4 spec rather than forcing weak static rules now. Both new rules follow the Batch 1 §1.1 rule-addition checklist, launch `experimental`, and promote to stable only on fixture plus real-repo evidence.

## 3.3 Thin VS Code extension (~3–5 days; parallel with 3.1)

In-editor presence for days of effort, and demand validation before any LSP bet (Batch 4).

- New workspace `editor/vscode-uptocode/` (TypeScript, esbuild bundle) — outside the Python package; own `package.json`.
- Behavior: on save of a Python file (and via a command), run `uptocode scan ${file} --format json` (settings: executable path, extra args, fail-on) and map findings to `vscode.Diagnostic`: severity map (critical→Error, warning→Warning, info→Information), `code` = rule id, `codeDescription.href` = first citation URL, range from finding line. Show analysis warnings in an output channel. No LSP, no daemon.
- Tests: unit-test the JSON→Diagnostic mapping with mocked `child_process` (include a malformed-JSON case). CI: a Node job that builds and tests the extension (keep the Python matrix untouched).
- ⛔ Operator: Marketplace publisher account + listing. Until then, document `.vsix` sideload in the README.

## Exit gate

Batch 1's command block per lane; docs/claims move in the same commits (README gains `fix` and extension sections; SPEC contract wording updated under 3.1's ⛔ ack); version bump + CHANGELOG at each lane landing; ⛔ operator pushes release tags.
