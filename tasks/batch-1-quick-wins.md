# Batch 1 — Quick Wins (rules, baseline debt, share-safe, distribution)

> Audience: Codex, no prior context needed. Ground rules: `tasks/completion-plan-v2.md` §6 (offline tests, strict contracts, deliberate goldens, docs move with code, Windows+POSIX, ⛔ operator gates, version sync across `pyproject.toml`/`uptocode/__init__.py`/`server.json`).
> **Prerequisite: the Devpost submission is confirmed by the operator.**
> Effort: ~1 week. Release as **1.1.0** at batch end with a CHANGELOG entry.
> Lanes A (rules), B (workflow), C (distribution) are independent and may run in parallel; each lane lands only through the exit gate.

## Lane A — two new high-frequency defect checks

### 1.1 New rule AA013 — Unbounded context growth (static, warning)

The most common real-world agent defect: message/history lists grow forever inside the loop.

- Evidence contract (conservative, positive-evidence only, per `docs/constitution.md`): inside a recognized loop (existing loop evidence), a list is `.append(...)`-ed AND that same name is passed as the messages/input/history argument of a recognized model call, AND no truncation evidence exists in the loop body or function: slice reassignment (`x = x[-N:]`, `x[:] = x[-N:]`), `del x[:N]`, `.pop(0)`/`.popleft()`, `deque(maxlen=…)`. Anything short of full recognition → coverage warning, never a silent pass and never a name-only guess.
- **Rule-addition checklist** (first new rule since 1.0 — reuse for every future rule):
  1. `uptocode/rules/core.yml` entry (id, name, tier `static`, severity `warning`, citations: Anthropic building-effective-agents, OpenAI practical guide PDF).
  2. Evaluator in `uptocode/rules/static.py` following the `_finding(...)` pattern.
  3. **Remove hardcoded rule ranges**: `uptocode/engine.py:74` (`range(1, 13)`), `engine.py:323` (hardcoded evaluated list), `engine.py:327` (`range(1, 13)`) — derive all three from the registry so future rules can't drift.
  4. `uptocode/mcp_server.py:133`: update the RuleId description text ("AA001 through AA012").
  5. README rule table row; `fixtures/bad_python` gains a positive case, `fixtures/clean_python` a clean counterpart.
  6. Goldens regenerated **deliberately in their own commit** with an explanation (GOAL.md hard rule).
  7. Tests per the SPEC contract: positive, clean, suppression (`# uptocode: ignore AA013`), unsupported-syntax, false-positive regression.

### 1.2 AA007 subcheck — retry without backoff (static, warning)

Extend AA007 (its timeout/retry evidence is already separated): when retry evidence exists but no backoff evidence, emit a third subcheck finding "Retry policy lacks backoff". Backoff evidence: `tenacity` `wait_exponential`/`wait_random_exponential`, sleep with a multiplied/exponential term, or the OpenAI client's built-in `max_retries` (SDK backoff is built in → clean). Same five-part test contract; update the README AA007 row.

## Lane B — workflow depth

### 1.3 Baseline-debt tracking

Today `--baseline` only mutes known findings. Upgrade `uptocode/baseline.py`:

- Baseline schema **2.1**: `entries: [{fingerprint, rule_id, file, first_seen}]`, with a back-compat loader for the 2.0 bare-fingerprints list.
- `apply_baseline` computes **new** (in scan, not baseline), **resolved** (in baseline, not scan), **aging** (in both; age from `first_seen`). Surface counts in `report.coverage` (`baseline_new`, `baseline_resolved` alongside existing `baseline_findings`) and a debt summary block in terminal + JSON output.
- `--update-baseline` preserves `first_seen` for persisting fingerprints (deterministic except genuinely new entries).
- Tests: three-scan lifecycle (introduce → persist → resolve) asserting all three buckets and `first_seen` stability. Content-based fingerprints make this exact.

### 1.4 Suppression metadata with expiry

Extend the directive parser in `uptocode/engine.py` (`_is_suppressed`, `# uptocode: ignore AA001`): optional trailing `owner=NAME reason="TEXT" expires=YYYY-MM-DD`.

- Bare directives keep working unchanged.
- Expired directives stop suppressing and add an analysis warning `SUPPRESSION_EXPIRED` (file, line, rule).
- Report gains a suppression detail list (file, line, rule, owner, reason, expires) — strict model addition, schema minor bump noted in CHANGELOG.
- Tests: bare, full-metadata, expiry-boundary (expires yesterday/today/tomorrow), malformed metadata → treated as bare + warning.

### 1.5 Share-safe report mode

`scan --share-safe`: replace `scan_root` with `<scan-root>`, keep `metadata.repository_revision`, and guarantee no absolute paths anywhere in JSON/HTML/SARIF output. Test: render all three formats for a scan under a deep absolute path and assert no drive-letter (`C:\`), POSIX-home (`/home/`, `/Users/`), or scan-root substrings appear.

## Lane C — distribution pack

### 1.6 Adoption surfaces

- `.pre-commit-hooks.yaml` at repo root: id `uptocode`, `language: python`, `entry: uptocode scan . --fail-on critical`, `pass_filenames: false`, `always_run: true`. Document in README (pre-commit snippet).
- README badges: PyPI version badge + a "scanned with UpToCode" badge snippet users can copy.
- ⛔ Operator: submit `server.json` to the MCP registry (it is ready); list the Action on GitHub Marketplace; create the missing GitHub Release for `v1.0.0` (tag exists, release object does not).

## Lane D — evidence base and rule maturity (from the 2026-07-20 reference review)

### 1.7 Citation architecture: registry-resolved, cross-vendor (fixes verified defects)

Two confirmed defects make the evidence base look OpenAI-only when it is not: `rules/static.py` hardcodes five OpenAI-only `Citation` constants and emits e.g. `[OPENAI_FUNCTIONS]` for AA004 even though `rules/core.yml` also lists Anthropic tool-definition guidance; `judgment.py` `_to_finding` flattens every citation to `vendor="Primary guidance", title="Rule guidance"` with a single URL.

- Make `core.yml` the single citation source of truth: each entry gains structured records — publisher, title, URL, and status (`normative`/`supporting`).
- Static evaluators stop passing hardcoded citation lists; findings resolve the full record set from the registry by rule id.
- Judgment validates the model-selected URL against the allowed set (unchanged), then attaches the **complete** structured records with real publisher/title.
- Add public cross-vendor references where applicable across existing rules: Anthropic tool-use loop and tool-error docs, the MCP specification, the NIST Generative-AI Profile (AI 600-1), and OWASP agentic-applications guidance. Public, accessible sources only (see `DECISIONS.md` D011).
- Tests: every emitted finding's citations equal the registry's for that rule; an AA004 finding shows both OpenAI and Anthropic records; no finding anywhere carries the literal strings "Primary guidance"/"Rule guidance".

### 1.8 AA001 remediation: protocol-aware termination first, cap as failsafe

Current `Verdict.recommended` is "Set a turn cap and preserve partial results" — vendor guidance treats an arbitrary cap **as the primary mechanism** as an anti-pattern. Rewrite remediation to: terminate on the framework's semantic completion signal (Agents SDK final output, LangGraph `END`, Anthropic `stop_reason` `end_turn` vs `tool_use`) as the primary control, with a hard turn/budget ceiling as the failsafe, preserving partial results at the ceiling. Detection is unchanged in this batch (Anthropic loop *recognition* arrives with the Batch 2 adapter); this is verdict/citation text plus tests.

### 1.9 Experimental rule maturity tier

Add `maturity: stable | experimental` to `core.yml` entries (default stable). Experimental rules: marked in every report surface, excluded from `--fail-on` unless `--include-experimental` is passed, listed separately in coverage. This is the rollout mechanism for all future guide-derived rules (Batch 3): observe first, promote to stable only after fixture and real-repo evidence. Tests: fail-on exclusion, flag inclusion, report marking.

## Exit gate (per lane, and again at batch end)

```text
python -m pytest -q && python scripts/acceptance.py && python scripts/compliance.py
python -m ruff check uptocode tests scripts && python -m mypy uptocode
python -m coverage run -m pytest -q && python -m coverage report   # ≥ 85%
cd web && npm test                                                  # unchanged, still must pass
```

Plus: README/docs claims match shipped behavior in the same commits; goldens changed only deliberately; bump 1.1.0 across `pyproject.toml`/`__init__.py`/`server.json`; CHANGELOG entry; tag `v1.1.0` (⛔ operator pushes the tag — it triggers the PyPI release workflow).
