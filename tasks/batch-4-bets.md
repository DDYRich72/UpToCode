# Batch 4 — Bigger Bets (spec-first; one at a time)

> Audience: Codex. Ground rules: `tasks/completion-plan-v2.md` §6.
> **Prerequisite: Batches 1–3 landed.** Every item here starts with a numbered spec in `specs/` and ⛔ operator acknowledgment **before** implementation — each one changes scope, a consent model, or infrastructure. Do not run these in parallel; pick one, land it, reassess.

## 4.1 Full LSP integration (2–4 weeks)

Upgrade the Batch 3 thin extension into a real language server (`pygls`), keeping the extension as the client.

- Spec must commit to: incremental single-file analysis with a latency budget (target <200 ms per save on a typical module), diagnostics parity with the CLI, code actions — "suppress with metadata" (emits the Batch 1 `# uptocode: ignore AAxxx owner=… reason=… expires=…` syntax), "open citation", "open FIXPLAN entry" — and explicit non-goals (no whole-repo background indexing in v1).
- Precondition worth honoring: this lands **after** the Batch 2 adapters — inline diagnostics are only as valuable as the frameworks recognized.
- Tests: pygls in-process client harness; per-rule diagnostic fixtures; suppression code-action round-trip.

## 4.2 Local-model judgment backend (~1 week + consent decision)

Same judgment tier, pointed at a local OpenAI-compatible endpoint (Ollama/LM Studio/GPT-OSS) so privacy-constrained orgs get judgment without code egress.

- ⛔ **Consent-model decision first** (GOAL.md §11: privacy-model changes are approval stops): proposal — `--judgment --local-url URL` does not require `--send-code`, because nothing leaves the machine; hosted/OpenAI judgment keeps double consent unchanged. Record the ruling in `DECISIONS.md` before any code.
- Implementation: backend abstraction over the existing judgment client; local backends often lack structured outputs, so add a fallback path — schema-in-prompt, strict Pydantic validation of the reply, one bounded repair retry, then the standard refusal/failure semantics (static results always preserved).
- Tests: mocked local endpoint (success, malformed JSON → repair → success, repair fails → `JUDGMENT_REFUSED`, timeout). Never a live model in CI.

## 4.3 Runtime evidence correlation (2–4 weeks; prototype gate)

Annotate static findings with whether the risky path was actually exercised at runtime.

- Spec first, scoped to **one** trace format for the prototype: OTLP GenAI/agent semantic-convention spans (or OpenAI Agents SDK trace export — pick whichever has the stablest schema at implementation time and cite it).
- `scan --traces FILE`: map spans to findings by file + qualified name; annotate findings `exercised_at_runtime: N` (strict-model addition). No tracing service, no collection — import only.
- Prototype gate: build the mapper against one recorded fixture trace and measure match quality before productizing. If mapping precision is poor, stop and record the finding — this one is allowed to fail cheap.

## 4.4 Hosted trend history (2+ weeks; requires reopening D005)

Findings-over-time per repo turns point-in-time scans into a quality dashboard — and is the **first** feature that justifies reviving the deferred Firestore plane.

- ⛔ Requires a new operator decision superseding `DECISIONS.md` D005's deferral, plus a spec covering: authenticated ingestion of **fingerprint counts and rule ids only** (never code, paths beyond repo-relative, or excerpts), retention/TTL, per-key isolation, and the dashboard surface on the site.
- Gate to even propose it: evidence of real hosted usage (key issuance and request volume). If the hosted beta is quiet, skip indefinitely — infrastructure without users is negative value.

## 4.5 Judgment-tier control rules: escalation/handoff and provenance (spec-first)

Deferred from Batch 3 §3.2b because their evidence is semantic, not syntactic: (a) escalation and structured-handoff quality — approval exists but escalation on inability-to-progress/policy gaps is absent, or handoffs carry no structured evidence summary; (b) provenance and temporal integrity in multi-source synthesis — claim-source mappings lost in summarization, conflicting values silently merged, missing publication dates. Both become **judgment-tier candidate extractors** (static code only *nominates* candidates — e.g., a recognized escalation tool, a synthesis step over multiple sources — and GPT judgment renders the verdict), launched `experimental` under the Batch 1 §1.9 tier. Spec must define candidate evidence precisely so the constitution's no-name-guessing rule holds; cite only public sources per `DECISIONS.md` D011. Pairs naturally with 4.2's judgment-backend work.

## Sequencing guidance

Default order: 4.1 → 4.2 → 4.3 → 4.4 (4.5 can ride alongside 4.2), but let demand reorder it — e.g., an enterprise privacy ask promotes 4.2 to first; heavy hosted usage promotes 4.4. Each item lands through the standard exit gate (Batch 1 command block, docs-with-code, deliberate goldens, version + CHANGELOG, ⛔ operator tags).
