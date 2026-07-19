# ArchAgent Completion Plan v2 — Competition-First, Always Submission-Ready

> **Supersedes** `tasks/production-workorder.md` and the prior "Public 1.0 Completion Plan". Where they conflict, this document wins.
> Official rules fetched 2026-07-19 from https://openai.devpost.com/rules and encoded in §2. Operator decisions recorded in `DECISIONS.md` (D005, D006).
> Audience: Codex, working in this repository with no other context.

## 1. Mission and operating principle

Win OpenAI Build Week (Developer Tools track), then continue to production 1.0. Two consequences:

1. **The repository must be submission-ready at the end of every phase.** No phase may end in a half-state. Every phase exits through the Submission-Ready Gate (§3) and a tagged release candidate. If the event deadline arrived mid-phase, the previous tag must be submittable as-is.
2. **Work is ordered by judged value.** The four judging criteria are equally weighted: Technological Implementation (skillful Codex use, working non-trivial implementation), Design (complete coherent product experience, not a proof of concept), Potential Impact, Quality of Idea. Build what judges see and touch first; back-office infrastructure last or not at all.

## 2. Official rules of record (binding)

| Requirement | Consequence for this repo |
|---|---|
| Submission period 2026-07-13 09:00 PT → **2026-07-21 17:00 PT** | Submit with buffer; target Monday evening PT. This repo's history began 2026-07-18, entirely inside the period — it qualifies as *newly created during the Submission Period*; no prior-work documentation is needed. |
| Video: **< 3 minutes**, clear demo **with audio**, covering *what you built and how you used Codex and GPT-5.6*, uploaded **publicly to YouTube**, no third-party trademarks/copyrighted material (no logos, no music) | Update `docs/demo-script.md`: keep the six-beat product demo, add an explicit beat on Codex-driven development and the GPT-5.6 Structured Outputs judgment tier. Operator records and uploads. |
| Repository: **public with licensing, or private and shared with `testing@devpost.com` and `build-week-event@openai.com`** | **Strategy: private repo shared with those two accounts.** This decouples the submission from PyPI publication and the unresolved package-name recheck entirely. MIT license already present. |
| README must describe **collaboration with Codex throughout development** | New required README section (§5, Phase 1). |
| Submission form requires a **Codex Session ID** for the core functionality thread | Operator captures from the Codex interface; stored in submission notes, not the repo. |
| Testing/demo access: website link, functioning demo, **or test build with credentials if private** | Minimum: exact local test-build instructions (clone → `pip install -e ".[test]"` → demo commands) in README. High-value optional: hosted MCP endpoint + judge credentials (§5, Phase 5). |
| Built with **Codex and GPT-5.6** (both required) | Already core: GPT-5.6 judgment tier, Codex-built repo, Codex-targeted FIXPLAN output. Say so explicitly in README, description, and video. |
| Original, solely owned work; no IP violations; no malicious code | MIT-licensed original work; keep dependencies audited. |

## 3. Submission-Ready Gate (run at every phase exit)

A phase is complete only when **all** of the following pass, in a clean environment, on Windows and POSIX:

```text
python -m pytest -q
python scripts/acceptance.py
python scripts/compliance.py
python -m ruff check archagent_audit tests scripts
python -m mypy archagent_audit
python -m coverage run -m pytest -q && python -m coverage report   # ≥ 85% branch
cd web && npm ci --ignore-scripts --no-audit --no-fund && npm test
```

Plus, every phase exit:

- [ ] README, `docs/demo-script.md`, and `docs/devpost-draft.md` claims exactly match the shipped surface (GOAL.md §7: claims must match).
- [ ] The demo sequence dry-runs end to end offline.
- [ ] Working tree clean; tag `v1.0.0-rc<N>` with a one-line summary of what the phase added.
- [ ] `PROGRESS.md` and `tasks/validation-report.md` updated in the same commits.

## 4. Locked decisions (operator-ratified — do not relitigate in specs)

- **D005 — Firestore access-control plane: deferred to 1.1.** Nothing is being "removed" — it was never built; it was a proposed addition. Its absence does not impede production readiness at private-beta scale: the SHA-256 key-hash allowlist plus the Phase 2 controls (rate limiting, hosted-judgment gate, key-prefix attribution) is a legitimate production posture for a manually provisioned beta, and judges receive credentials directly in submission notes — they will never see or exercise a request-access flow. Building it before the deadline would spend the largest single block of remaining effort on surface judges cannot observe, while adding this project's first PII store and a public unauthenticated endpoint days before judging. Write `specs/003-beta-access-control.md` as a **1.1 spec** if desired; land no Firestore code in 1.0.
- **D006 — Submission via private repository sharing.** The repo stays private and is shared with the two rule-specified accounts. PyPI publication, MCP registry submission, and the package-name recheck are **post-event** work and no longer block anything in Track A.
- **Drizzle/D1 removal: approved cleanup.** Verified unused (empty schema, `getDb()` imported by nothing). Remove packages, `web/db/`, `web/drizzle.config.ts`, the drizzle copy step in the vite plugin, and related examples in Phase 4. Zero functional effect.
- **TypeScript: 1.1**, own spec, real parser, explicit per-language rule applicability. No TS code in 1.0.
- **Adopted from the prior Codex plan:** SARIF upload completes before the composite Action fails on findings; dependency audit runs against a wheel-installed environment; `web/build/sites-vite-plugin.ts` moves out of the gitignored `build/` path before first push; CI gains job timeouts, concurrency cancellation, and `tsc --noEmit`.

## 5. Phases (each exits through §3)

### Phase 0 — Preserve and verify → `v1.0.0-rc1`

The entire production build (~1,560 changed lines, 27 untracked paths) is uncommitted on `codex/archagent-build`.

- [ ] Verify ignores (`web/node_modules/`, `web/dist/`, `web/.wrangler/`; `web/.vinext/` only if regenerated by build; `.archagent-audit/` outputs stay ignored). Move `web/build/sites-vite-plugin.ts` to a tracked path (e.g. `web/plugins/`) now so nothing tracked lives under an ignored directory.
- [ ] Commit the working tree as a logical series of conventional commits.
- [ ] Clean-room verification per §3 from a fresh venv; replace every claim in `tasks/validation-report.md` with fresh evidence.

### Phase 1 — Rules compliance and submission assets → `rc2`

Everything the Devpost form and video need, done early so every later tag is submittable.

- [ ] `docs/event-rules.md`: the §2 table expanded into a checklist with owner (Codex vs operator ⛔) per item.
- [ ] README: add the required **"Built with Codex"** section — how Codex was used throughout (gates, FIXPLAN hand-offs, this plan), plus how GPT-5.6 powers the judgment tier; add exact judge test-build instructions (clone → install → `archagent-audit scan fixtures/bad_python` → review → plan → `serve`). Optional, operator's choice: one truthful sentence noting that independent AI code review produced the work orders Codex executed (the rules require no such disclosure; the planning documents are in the repo either way).
- [ ] Update `docs/demo-script.md`: six product beats + the Codex/GPT-5.6 usage beat; every on-screen claim demoable; note the no-trademarks/no-music constraint for recording.
- [ ] Refresh `docs/devpost-draft.md` against the real shipped surface (ten local MCP tools, hosted mode, SARIF, baselines, rule selection — or deliberately trim to the demo subset).
- [ ] Capture the evidence set it lists (bad-fixture terminal scan, HTML report views, redacted AA006, manifest + FIXPLAN, MCP `check_loop` response, acceptance PASS, validation matrix) into `docs/submission-evidence/`.
- [ ] ⛔ Operator: capture the **Codex Session ID** for the core-functionality thread; keep with submission notes.

### Phase 2 — MCP hardening (judges will poke this) → `rc3`

- [ ] Containment: resolve the effective local root once in `create_server`; every path-bearing tool on every instance (including the module-level server) uses it and rejects outside paths. Test proves it.
- [ ] FastMCP strict-schema shim: guard every private attribute; clear startup error naming the installed MCP version on mismatch; upgrade canary + playbook in `docs/operations.md`.
- [ ] Remove vestigial `judgment`/`send_code` from `check_tool_schema`.
- [ ] Hosted minimal controls: in-memory per-key rate limit (env-tunable, default 30/min, `429` + `Retry-After`), `ARCHAGENT_HOSTED_JUDGMENT` gate default **off**, safe key-prefix in logs. (This replaces the Firestore plane for 1.0.)
- [ ] Compliance enforces version agreement (`pyproject.toml` = `__init__.py` = `server.json`).

### Phase 3 — GitHub and CI surface → `rc4`

- [ ] ⛔ Operator: create the **private** GitHub repo and push (low-risk; private repos run Actions and enable judge sharing). Then burn in CI.
- [ ] CI fixes from the adopted plan: split dependency audit from the 9-cell matrix; audit the wheel-installed environment; timeouts; concurrency cancellation; site lint + `tsc --noEmit`; container smoke (`/healthz` 200, unauthenticated `/mcp` 401); artifact retention.
- [ ] Reporters: GitHub workflow-command escaping (`%`→`%25`, CR→`%0D`, LF→`%0A`; properties also `:`→`%3A`, `,`→`%2C`) in a dedicated reporter module; SARIF omits absent keys (no `null`), adds per-rule default level; tests include hostile messages and a no-null assertion.
- [ ] `--github-summary PATH` (auto-append to `GITHUB_STEP_SUMMARY` when set and no path given): severity totals, coverage, warnings, bounded top-findings table.
- [ ] Composite `action.yml`: inputs `path`/`fail-on`/`version`/`upload-sarif`; installs pinned version; **uploads SARIF before failing**; preserves scanner exit code; YAML contract test.
- [ ] SHA-pin all action `uses:` (tag in comment); add weekly Dependabot for actions/pip/npm.
- [ ] Record the green run URL, matrix, and coverage in the validation report.

### Phase 4 — Design-criterion polish → `rc5`

- [ ] Site: remove Drizzle/D1 and starter copy; disposition the two moderate Next/PostCSS advisories (upgrade or written accepted-risk note in `SECURITY.md`); keep landing + `/connect` sharp; accessibility pass (keyboard, reduced motion) on both routes.
- [ ] `CHANGELOG.md` 1.0.0 entry matching reality; docs sync (`serve` flags, hosted env vars, baseline/SARIF/changed-since examples, action usage).
- [ ] Self-scan story sharpened for the demo: `scripts/compliance.py` zero-findings evidence is a headline beat ("ArchAgent audits itself").

### Phase 5 (optional, high value) — Hosted judge access → `rc6`

Rules are already satisfied by test-build instructions; do this only if time remains after rc5.

- [ ] ⛔ Operator: deploy Cloud Run privately with real secrets; generate judge keys into the env allowlist; verify `/healthz`, 401, rate limit, and an AA001 call against the live URL.
- [ ] Add judge credentials + endpoint to submission notes (never the repo). Add the hosted URL to `server.json` `remotes`.

### Phase 6 — ⛔ SUBMIT (operator, target Monday evening PT)

1. Final §3 gate on the candidate tag → retag `v1.0.0-submission`.
2. Share the private repo with `testing@devpost.com` and `build-week-event@openai.com`.
3. Record the < 3-minute video per the script (audio narration; what was built + how Codex and GPT-5.6 were used; no third-party marks/music); upload to YouTube as **public**.
4. Complete the Devpost form: description, video URL, repo access, **Codex Session ID**, testing instructions (+ judge credentials if Phase 5 ran).
5. Submit; record the submission URL and timestamp in `PROGRESS.md`. No further pushes to the submitted tag's branch until results.

### Phase 7 — Post-event production train (unblocked, unhurried)

PyPI name recheck → trusted publishing → tag-driven release with SBOM/provenance → public repo decision → MCP registry submission with final `server.json` → post-deploy authorized live GPT-5.6 smoke → `specs/003` (beta access, Firestore) and TypeScript as 1.1 specs.

## 6. Standing rules

1. ⛔ Operator-only: creating remotes/repos, sharing access, publishing packages or releases, deploying, uploading video, submitting, distributing keys, any paid model call.
2. All ordinary tests offline/mocked; static scans make no network calls; consent gates (`judgment` ⇒ `send_code`) and redaction are never weakened.
3. Strict contracts everywhere (`extra="forbid"`); goldens regenerate only deliberately, same-commit, with explanation.
4. No self-approved scope: new stores, endpoints, or subsystems require an operator decision in `DECISIONS.md` first.
5. Docs move with code in the same commit; Windows and POSIX both green before any tag.
