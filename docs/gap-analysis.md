# UpToCode — Gap Analysis and Completion Plan

> Drafted 2026-07-19 from a post-Gate-4 review of `codex/uptocode-build` at `f3154a8` (133 tests passing on Windows 3.11/3.13 and Ubuntu/WSL 3.13).
> Companion to `roadmap.md` (MVP gates). This document covers what remains between the shipped MVP and a complete, robust tool and MCP server.
> Event context: the OpenAI Build Week deadline is Tuesday, 2026-07-21 17:00 PT. See "Pre-submission vs post-submission" in section 6.

## 1. Verdict

The committed MVP core is sound: consent-gated judgment, redaction before egress, fail-closed coverage warnings, deterministic reports, manifest-bound approvals, and cross-platform acceptance evidence. Remaining work clusters into six areas, ordered by leverage:

1. Five confirmed robustness defects (all small fixes).
2. MCP completion — the server currently exposes a fraction of the product.
3. CI adoption — stable fingerprints, baseline mode, SARIF.
4. Configuration, engine quality, and judgment hardening.
5. Rulepack extensibility (claimed in the demo script, not yet implemented).
6. Release engineering and (approval-gated) publication.

## 2. Confirmed defects (verified against the working tree)

| ID | Defect | Where | Contract violated |
|---|---|---|---|
| D1 | Malformed `.uptocode.yml` produces an unhandled `yaml.YAMLError` traceback. `load_config` calls `yaml.safe_load` unguarded; the CLI catches only `OSError`/`ValueError`. Reproduced. | `config.py`, `cli.py` | "Exit 2 for invalid configuration" with a clean message |
| D2 | A single unreadable file aborts the entire scan. The per-file loop catches `UnicodeDecodeError`/`SyntaxError` but not `OSError` (permissions, deletion race). Discovery's `stat`/`read_bytes` are also unguarded. | `engine.py`, `config.py` | Degraded files should become analysis warnings, not scan aborts |
| D3 | No `--version` flag; `python -m uptocode` fails (no `__main__.py`); `Report.tool_version` defaults to a hardcoded string duplicating `__version__`. | `cli.py`, `models.py`, package root | Version drift risk; basic CLI ergonomics |
| D4 | The CLI cannot scan a single file (`scan_path` requires a directory) while MCP `audit_file` can. | `engine.py`, `cli.py` | Surface asymmetry with no rationale |
| D5 | MCP `audit_file`/`audit_diff` silently return an empty, clean-looking report when input exceeds the 1 MiB size limit — the file is skipped at discovery and the CLI's `files_discovered && !files_analyzed` exit-2 guard is not replicated in `_scan_source`. | `mcp_server.py` | "Unsupported code is never silently declared clean" |

## 3. Gaps for a complete tool

### 3.1 CI adoption (highest leverage)

- No SARIF reporter. `--format github` is a stub that exits 2. SARIF 2.1.0 is the standard for GitHub code scanning and PR annotation and largely obsoletes a bespoke GitHub reporter.
- No baseline mode ("record existing findings, fail only on new"). Brownfield repositories cannot adopt the tool without it.
- Fingerprints are line-number-based: `sha256(rule|file|line|kind)` in `rules/static.py` (judgment findings likewise). Any edit above a finding shifts its line and changes the fingerprint. This breaks future baselines and already breaks review continuity: the manifest binds to the exact report fingerprint, so every rescan invalidates all prior approve/reject decisions with no carry-forward path.
- No changed-files or incremental mode in the CLI (`audit_diff` exists only on MCP).
- No scan duration or timing metadata in the report.
- The repository itself has no CI: no `.github/workflows`, no lint or type-check configuration, no coverage measurement.

### 3.2 Configuration and engine quality

- No rule selection (`--select`/`--ignore`), no per-rule severity overrides, no `--exclude` CLI flag (config file only).
- Only the root `.gitignore` is honored; nested ignore files are not.
- `rglob("*.py")` descends into excluded trees before filtering — the recorded self-scan waded through 6,242 excluded files in local environments. A pruned walk skips excluded directories before descent.
- No `--verbose`/`--debug` logging.

### 3.3 Judgment tier

- Model (`gpt-5.6`), 30 s timeout, 2,000-token output cap, and six-rule budget are all hardcoded; no env/config override for model or base URL.
- Error classification matches exception type-name substrings ("timeout" in name) instead of the openai SDK's typed exceptions; rate limits collapse into the generic API error code. `except BaseException` also swallows `KeyboardInterrupt`.
- The report does not record which model produced judgment findings or token usage — an auditability gap for a tool whose pitch is evidence.
- No caching of identical candidate payloads between runs (repeat runs re-bill).

### 3.4 Extensibility

- Rules are hardcoded Python modules; `rules/core.yml` carries metadata only. There is no plugin API or external-rulepack loading, so organization-specific rules require forking. The demo script's closing claim ("rulepack extensibility") is not yet true.

### 3.5 Release engineering

- No `py.typed` marker, no CHANGELOG, CONTRIBUTING, or SECURITY docs, no lint/type-check config, no coverage gate, no release workflow. Publication remains blocked on the documented name recheck and explicit approval.

## 4. Gaps for a complete MCP server

1. **No repo-level scan tool.** The five tools audit one file, a diff snippet, a loop snippet, a schema, or fetch rule metadata. An agent working inside a project cannot say "audit this project" — the flagship CLI capability is absent. `audit_file` additionally copies the target into a temp directory, losing the project's `.uptocode.yml`, gitignore context, and real relative paths (`scan_root` becomes `<submitted-code>`).
2. **The review/plan workflow — the product differentiator — has no MCP surface.** An agent cannot approve findings or retrieve a FIXPLAN over MCP.
3. **Protocol features unused:** no tool annotations (all five tools qualify for `readOnlyHint`), no typed output schemas (tools return `dict[str, Any]`, so clients receive no `outputSchema`), no resources or prompts, no progress reporting for long scans, no declared server version.
4. **Filesystem scope is unbounded** — `audit_file` reads any path the process can read. Tolerable for local stdio; a roots/allowlist mechanism is required before any other transport.
5. **stdio only** — no streamable-HTTP transport option for remote or shared use.
6. **Distribution:** registration requires a repo-checkout `cwd`; the complete story is PyPI publication → `uvx uptocode serve` one-liner → `server.json` and MCP registry listing (all approval-gated).

## 5. Non-goals (unchanged from SPEC)

TypeScript support, instruction-file linting, runtime tracing, and source-changing auto-fix remain out of scope. Nothing in this plan requires revisiting them.

## 6. Completion plan

Sizes are focused dev-days for one implementer keeping the existing test discipline: every item lands with tests, and goldens regenerate only deliberately.

### Pre-submission vs post-submission

The event deadline is 2026-07-21 17:00 PT. Recommended split, in the spirit of the Monday-noon cut policy:

- **Before submission:** Phase 0 only. The five defect fixes are small, low-risk, and close contract violations a judge could plausibly hit (malformed config, oversized MCP input, missing `--version`). Freeze after Phase 0 and re-run the full acceptance evidence.
- **After submission:** Phases 1–6. Do not destabilize the MCP surface or fingerprint scheme within 48 hours of the deadline.

### Phase 0 — Defect fixes (~1 day)

- [ ] D1: wrap config parsing; map YAML and validation errors to a clean exit-2 configuration error. Test with a malformed-YAML fixture.
- [ ] D2: per-file `OSError` becomes a `FILE_READ_ERROR` analysis warning; guard discovery's `stat`/`read_bytes`. Test via mock-raised `OSError` (chmod-based tests are unreliable on Windows).
- [ ] D3: add an eager `--version` option; add `uptocode/__main__.py`; source `Report.tool_version`'s default from `__version__`.
- [ ] D4: accept a single `.py` file as the scan target in `scan_path` and the CLI.
- [ ] D5: `_scan_source` returns a structured error when discovery finds input but nothing was analyzable.

Acceptance: new paths covered by tests; `python -m pytest -q` and `python scripts/acceptance.py` stay green on Windows and POSIX.

### Phase 1 — MCP completion (1–2 days)

- [ ] `audit_repo(path, judgment=False, send_code=False)`: runs `scan_path` in place, honoring `.uptocode.yml`, gitignore, suppressions, and real relative paths.
- [ ] `review_findings(report_json, approve, reject, approve_all)` → manifest JSON, and `generate_fixplan(report_json, manifest_json)` → FIXPLAN markdown. Pure functions over supplied payloads; no hidden filesystem state.
- [ ] Tool annotations: `readOnlyHint` (and `idempotentHint` where true) on every tool.
- [ ] Typed outputs: return Pydantic models (`Report`, manifest, issue lists) so FastMCP emits `outputSchema`.
- [ ] Declare the server version; expose the rule catalog as a resource or `list_rules` tool.
- [ ] Input hardening: cap snippet/diff sizes with a clear error before any temp write.
- [ ] Optional: `Context.report_progress` during `audit_repo` on large trees.

Acceptance: MCP tests cover the new tools, annotations, and schema presence; the stdio acceptance run still passes.

### Phase 2 — CI adoption (2–3 days)

- [ ] Content-based fingerprints: hash rule id plus normalized excerpt/context rather than line numbers; keep line for display. Regenerate `tests/golden/bad_python_fingerprints.json` in the same commit; bump report `schema_version` to `1.1` and document that fingerprints are not comparable across schema versions.
- [ ] Baseline mode: `scan --baseline FILE` (suppress known findings, count them in coverage) and `--update-baseline`; `--fail-on` evaluates new findings only when a baseline is active.
- [ ] Manifest carry-forward: `review --reuse MANIFEST` re-applies prior decisions to a new report by stable fingerprint; unmatched decisions are reported, never silently dropped.
- [ ] SARIF 2.1.0 reporter (`--format sarif`): severity → SARIF level, fingerprints → `partialFingerprints`, citations → help URIs; validate against the SARIF schema in tests. Retire or reimplement the `github` stub on top of SARIF.
- [ ] Changed-files mode: `scan --files ...` and/or `--diff-base REF` (CLI parity with `audit_diff` but with real files and real config).
- [ ] Record scan duration in report metadata.

Dependency: fingerprints land first; baseline and carry-forward build on them. SARIF is independent and can proceed in parallel.

### Phase 3 — Configuration and engine quality (1–2 days)

- [ ] `--select`/`--ignore` CLI filters plus a `rules:` config block (enable/disable, severity overrides).
- [ ] `--exclude` CLI flag merged with config excludes.
- [ ] Nested `.gitignore` support; replace `rglob` with a pruned walk that skips excluded directories before descent.
- [ ] `--verbose` logging with timings; default output unchanged.

### Phase 4 — Judgment hardening (~1 day)

- [ ] Configuration surface (env, `.uptocode.yml`, flags) for model, base URL, timeout, output-token cap, and rule budget; default remains `gpt-5.6`.
- [ ] Replace name-substring matching with openai typed exceptions (`APITimeoutError`, `AuthenticationError`, `PermissionDeniedError`, `RateLimitError` → distinct warning codes); catch `Exception`, let `KeyboardInterrupt`/`SystemExit` propagate.
- [ ] Record the judgment model id and per-rule token usage in the report.
- [ ] Optional: candidate-payload cache keyed by content hash to avoid re-billing identical reruns.

Live-API behavior stays mocked in tests; any paid smoke run remains explicitly approval-gated per the constitution.

### Phase 5 — Rulepack extensibility (1–2 days)

- [ ] Define and document a versioned rule API (normalized evidence in → findings/warnings out).
- [ ] Load external rulepacks from config (paths and/or entry points); namespace custom rule ids to avoid `AA` collisions.
- [ ] Ship one documented example rulepack with tests; a pack that fails to load is a clean configuration error, never a silent skip.

### Phase 6 — Release engineering (~1 day + approval-gated externals)

- [ ] GitHub Actions: test matrix (3.11–3.13 × ubuntu/windows/macos), ruff, mypy, coverage gate, acceptance runner.
- [ ] `py.typed`, CHANGELOG.md, CONTRIBUTING.md, SECURITY.md.
- [ ] Tag-driven build/publish workflow (PyPI trusted publishing). **Publication requires the name recheck and explicit approval per SPEC.**
- [ ] Post-publication: `uvx uptocode serve` docs, `server.json`, MCP registry submission — approval-gated.
- [ ] Optional: streamable-HTTP transport behind a flag, gated on the roots/allowlist hardening from Phase 1.

### Sequencing summary

Phase 0 → 1 → 2 is the critical path (defects → MCP completeness → CI adoption). Phases 3–5 can interleave once Phase 2's fingerprint work has landed; Phase 6's internal items can start at any time, external items last. Total: roughly 8–12 focused days.

### Risks

- The fingerprint migration touches goldens and manifest semantics — do it in one commit with regenerated goldens and the schema-version note, per the existing golden-change discipline.
- SARIF consumers vary; schema-validate the output in tests rather than eyeballing one viewer.
- Typed MCP outputs change tool result shapes for existing clients; declare the server version and note the change.
