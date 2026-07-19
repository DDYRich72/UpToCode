# Phase 4 Validation Matrix

Verified implementation commits: `b07a34a` (`feat(web): polish competition surface`) and
`6e396ea` (`fix(web): ignore TypeScript build state`). Phase 3 remains preserved as
`v1.0.0-rc4` at corrected commit `4fe8a61`; exact-tag CI run `29706598903` and artifact
run `29706598904` passed. All Phase 4 model calls were mocked/offline; no deployment,
publication, key distribution, or submission action occurred.

| Gate | Windows clean clone | Ubuntu/WSL clean clone |
|---|---|---|
| Runtime | Python 3.13.7; Node 22.19.0 | Python 3.13.12; Node 22.22.2 |
| `python -m pytest -q` | PASS — 175 | PASS — 175 |
| `python scripts/acceptance.py` | PASS — 175 tests, real stdio 10-tool probe and AA001 response | PASS — same |
| `python scripts/compliance.py` | PASS — zero production findings, warnings, suppressions; version contract synchronized at 1.0.0 | PASS — same |
| Ruff | PASS | PASS |
| strict mypy | PASS — 30 source files | PASS — 30 source files |
| branch coverage | PASS — 88% | PASS — 88% |
| clean `npm ci` | PASS — 493 packages | PASS — 494 packages |
| site lint / `tsc --noEmit` | PASS | PASS |
| site production build | PASS — `/`, `/connect` | PASS — `/`, `/connect` |
| rendered/site contract tests | PASS — 5 | PASS — 5 |
| production npm audit | PASS release threshold — no high/critical; two documented moderate Next/PostCSS records | PASS — same |
| offline demo dry-run | PASS; critical scan exited 1, ten findings/three redactions, artifact commands exited 0 | PASS — same |
| Git tree | Clean; generated TypeScript build state ignored | Clean; generated TypeScript build state ignored |

Browser verification against the real Wrangler asset binding passed at desktop and 375px
mobile widths: `/`, `/connect`, CSS, JavaScript, and RSC requests returned 200; there were
no console errors, overlays, or horizontal overflow; and ArrowRight moved both focus and
selection to the Hosted MCP tab. TypeScript analysis remains 1.1 scope; the site-only
`tsc --noEmit` check does not change that claim. Repository sharing, video upload, and
Devpost submission remain operator-only.
