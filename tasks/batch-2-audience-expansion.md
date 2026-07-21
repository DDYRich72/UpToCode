# Batch 2 — Audience Expansion (framework adapters, TypeScript, interactive review)

> Audience: Codex. Ground rules: `tasks/completion-plan-v2.md` §6. Rule-addition/adapter discipline from `tasks/batch-1-quick-wins.md` §1.1 checklist.
> **Prerequisite: Batch 1 landed** (registry-driven rule counts; checklist exists).
> Three lanes with near-zero file overlap — run in parallel; each lane lands independently through the exit gate. Release train: 1.2.0 when the first lane lands; minor bumps as later lanes land.

## Lane A — Python framework adapters (~3–5 days each; ship one at a time)

Highest ROI in the program: each adapter reuses all rules, reporters, MCP tools, the Action, and baselines. Keep framework specifics behind the normalized evidence contract (GOAL.md hard rule: no second rule engine).

### 2A.0 Per-adapter method (applies to each)

1. **Framework contract memo first** (`docs/frameworks/<name>.md`): the SDK's actual loop/budget/timeout defaults with citations to its docs — because clean-by-default vs flagged depends on documented defaults (precedent: `Runner.run` omitted `max_turns` is clean because the SDK default is bounded).
2. Evidence extractor `uptocode/adapters/<name>.py` emitting the existing normalized structures (loops with `bound_kind`, tools with provenance, model calls, timeout/retry facts). Unrecognized constructs → coverage warnings, never silent.
3. `frameworks_detected` value, README supported/unsupported constructs section, `fixtures/bad_<name>` + `fixtures/clean_<name>`, goldens (deliberate commit), five-part rule tests for each rule the adapter feeds.

### 2A.1 Anthropic / Claude SDK (promoted to first — vendor-neutrality is the product claim)

Recognize the documented Claude agent-loop contract (public docs: how-tool-use-works): a `messages` loop that continues on `stop_reason == "tool_use"` and terminates on `"end_turn"` is **bounded-by-protocol evidence** for AA001 (with or without an additional cap; cap-plus-signal is the ideal). Conversely, loops that parse assistant text for completion, or use an arbitrary cap as the *only* mechanism, remain AA001 candidates per the vendor's own anti-pattern list. Also recognize: `max_tokens` → AA002, client timeout/retry configuration → AA007, tool definitions in `tools=[...]` dicts and Agent SDK `@tool` → AA003/AA004 provenance, Agent SDK hooks (`PreToolUse`/`PostToolUse`) as programmatic-enforcement evidence feeding AA003. Fixtures `bad_anthropic`/`clean_anthropic`.

### 2A.2 CrewAI

Recognize: `Agent(max_iter=…, max_execution_time=…)`, `Crew(...)`/`kickoff()` execution, `@tool` decorator provenance (feeds AA003/AA004), `Process.sequential|hierarchical` facts. Bounds map to AA001/AA002; execution-time to AA007 evidence.

### 2A.3 PydanticAI

Recognize: `Agent(...)`, `run/run_sync/run_stream`, `UsageLimits(request_limit=…, total_tokens_limit=…)` → AA002 evidence, `@agent.tool` provenance, model-settings timeout → AA007.

### 2A.4 Fourth adapter

AutoGen/AG2 (`max_consecutive_auto_reply`, `GroupChat(max_round=…)`) **or** LlamaIndex agents — pick by current PyPI download counts at implementation time; record the choice in `DECISIONS.md`.

## Lane B — TypeScript subset (~2–3 weeks)

**Step 1 is a spec**: author `specs/004-typescript-analysis.md` (TS was declared out of 1.0 scope; per `DECISIONS.md` it needs its own spec) and get ⛔ operator acknowledgment before implementation.

Committed subset — everything else is explicitly per-language not-applicable; TypeScript must never be silently declared clean:

- Parser: `py-tree-sitter` + `tree-sitter-typescript` (prebuilt wheels; prove availability on the 3.11–3.13 × Ubuntu/Windows/macOS CI matrix before writing rules). No Node runtime requirement, no regex heuristics.
- Discovery: `.ts`/`.tsx`/`.mts` (reuse size/binary/gitignore handling; `node_modules/` already excluded).
- Evidence → existing rules: `while (true)`/`for (;;)` without exit → AA001; OpenAI Agents JS `run(agent, {maxTurns})` and LangGraph.js `recursionLimit` → AA001 bounds; `maxTokens`/`max_output_tokens` → AA002; `AbortSignal.timeout`, client timeout options, retry config → AA007; tracing imports → AA012; `tool({ parameters: z.object(...) })` zod presence → partial AA004.
- Report: coverage gains per-language `rules_evaluated`/`rules_not_applicable` (strict-model addition, minor schema bump).
- MCP: relax the hardcoded `.py` filename gate in `_scan_sources`/`audit_source` to the supported-extension set.
- `fixtures/bad_ts` + `fixtures/clean_ts`, goldens, README language matrix, unsupported-construct warnings.

## Lane C — interactive review in the standalone HTML report (~1 week)

Goal: approve/reject findings and download a **report-bound** manifest directly from the HTML report, retaining the non-mutating contract (the manifest is consumed by the existing `uptocode plan`).

- CSP today is `default-src 'none'; style-src 'unsafe-inline'; img-src data:` — scripts are blocked. Make a **deliberate, documented** change: add `script-src 'unsafe-inline'`. Rationale to record: `default-src 'none'` still blocks all network egress; the report is a static local file; all embedded JSON must escape the characters `<`, `>`, and `&` using JSON unicode escapes (the backslash-u003c / u003e / u0026 forms, as `json.dumps` produces when configured) so hostile finding text cannot break out of the script block or close it early — extend the existing XSS tests to the script payload.
- Embed `report_fingerprint` at render time (reuse `uptocode.review.report_fingerprint`). The downloaded manifest must be byte-shape-identical to `create_manifest` output: `{schema_version: "2.0", report_fingerprint, created_at, decisions: [{fingerprint, status}]}`.
- UI: per-finding Approve/Reject toggles (keyboard-accessible, visible state), decision counter, "Download review manifest" button (Blob download, no network).
- Tests (Python, offline): embedded fingerprint equals `report_fingerprint(report)`; hostile finding text cannot escape the JSON script block; manifest template fields match the `ReviewManifest` model. Plus one documented manual dry-run: download a manifest in a browser and run `uptocode plan report.json --manifest downloaded.json` successfully.

## Exit gate

Same command block as Batch 1, per lane. Each lane: docs/claims in the same commits, deliberate goldens, version + CHANGELOG at lane landing, ⛔ operator pushes release tags.
