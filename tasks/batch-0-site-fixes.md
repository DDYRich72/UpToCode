# Batch 0 — Site Fixes and Workspace Hygiene

> Audience: Codex, no prior context needed. Companion: `tasks/completion-plan-v2.md` (ground rules §6 apply), QA findings of 2026-07-20.
> **Timing: this batch MAY land before the Devpost deadline** — item 0.1 is a judge-facing correctness defect. Batches 1–4 wait until the submission is confirmed.
> Effort: a few hours. No Python package changes, no version bump.
> **Status note (2026-07-20):** Codex is already fixing its own QA findings, which overlap items 0.1, 0.2, and parts of 0.4. This file is therefore the **acceptance checklist** for that work plus the remainder: verify 0.1 covers BOTH lines 16 and 19, then complete 0.3, the junk-dir and recovery-dir deletions in 0.4, and the ⛔ deploys in 0.5.

## 0.1 Fix invalid TOML from the connection generator (High)

`web/app/connect/ConnectGenerator.tsx` lines 16 and 19 escape only double quotes (`replaceAll('"', '\\"')`). A Windows root such as `D:\work\sample-agent` produces invalid TOML — reproduced with a real parser: `TOMLDecodeError: Unescaped '\' in a string`. Newlines in input could also inject TOML fields.

- Factor config generation into a plain-JS module (e.g. `web/app/connect/toml.mjs`) exporting `tomlBasicString(value)` and `buildConfig(mode, endpoint, root)` so both the component and node tests import the same code.
- `tomlBasicString` must: escape backslash **first** (`\` → `\\`), then `"` → `\"`, and strip or reject control characters (U+0000–U+001F, U+007F). Apply to **both** the local `root` and the hosted `endpoint` values.
- Tests (`web/tests/connect-config.test.mjs`, node --test): generate configs for `D:\work\sample-agent`, values containing `"`, a trailing backslash, mixed `\"` sequences, and an attempted `\n` injection — parse each with a real TOML parser (add devDependency `smol-toml`) and assert the parsed `--root`/`url` round-trips to the original input.

Acceptance: hostile inputs produce parseable TOML that round-trips; existing rendered-HTML tests still pass.

## 0.2 Fix missing spaces around inline code (Medium)

`web/app/connect/page.tsx` lines 25–28: JSX swallows the newline between trailing text and `<code>`, rendering `address,https://…` and `localUPTOCODE_API_KEY`. Add `{" "}` before both `<code>` elements. Extend the rendered-HTML test to assert the space is present.

## 0.3 Announce copy success through the live region (Low)

`ConnectGenerator.tsx`: the `role="status" aria-live="polite"` span currently announces only failure; success is conveyed only by the button label change, which screen readers do not announce. Render success text (e.g. "Configuration copied.") through the same live region. Test: rendered output includes the status span; component logic sets success text.

## 0.4 Workspace hygiene and guardrails

Local debris from interrupted tool runs is poisoning local QA (CI is unaffected):

- Delete `web/node_modules.local-stalled-20260720`, `node_modules.partial-20260719-0304`, `node_modules.phase4-current`, `node_modules.phase4-partial`, `node_modules.stalled-20260719`, `node_modules.stalled-20260719-2`, then run a clean `npm ci` in `web/`.
- Delete the junk repo-root directory literally named `C:Usersnokes` (contains only an empty `.uptocode`).
- `python -m pip uninstall -y archagent-audit`, then `python -m pip check` must be clean (it currently reports the stale pre-rename editable dist).
- Guardrails so recurrence can't poison QA: add `node_modules*/**` to `globalIgnores` in `web/eslint.config.mjs` and `"node_modules*"` to `exclude` in `web/tsconfig.json` (today they cover only plain `node_modules`, so `npm run lint` traversed ~19,900 third-party problems).

Acceptance: `npm run lint` and `tsc --noEmit` in `web/` are clean; `pip check` clean; junk paths gone.

## 0.5 ⛔ Operator deploys

- Redeploy the site with 0.1–0.3.
- Optional but recommended: redeploy the current MCP image and re-probe — the live service's `/healthz` currently returns an edge 404 while `/readyz` and `/mcp` work; the running revision predates HEAD.

## Exit gate

`python -m pytest -q` (unchanged, run anyway) · `cd web && npm ci && npm test && npm run lint && npx tsc --noEmit` · CI green on push · claims unchanged (no README/scope changes needed).
