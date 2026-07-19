# Phase 2 Validation Matrix

Verified commit: `0d07f71` (`feat(mcp): harden local and hosted controls`). All model
calls were mocked/offline; no deployment, publication, key distribution, or submission
action occurred.

| Gate | Windows clean clone | Ubuntu/WSL clean clone |
|---|---|---|
| Runtime | Python 3.13.7; Node 24.14.1 | Python 3.13.12; Node 22.22.2 |
| `python -m pytest -q` | PASS — 167 | PASS — 167 |
| `python scripts/acceptance.py` | PASS — 167 tests, real stdio 10-tool probe and AA001 response | PASS — same |
| `python scripts/compliance.py` | PASS — zero production findings, warnings, suppressions; version contract synchronized at 1.0.0 | PASS — same |
| Ruff | PASS | PASS |
| strict mypy | PASS — 29 source files | PASS — 29 source files |
| branch coverage | PASS — 87% | PASS — 87% |
| clean `npm ci` | PASS — 506 packages; one non-fatal optional nested-WASM cleanup warning | PASS — 507 packages |
| site production build | PASS — `/`, `/connect` | PASS — `/`, `/connect` |
| rendered site tests | PASS — 2 | PASS — 2 |
| offline demo dry-run | PASS on exact commit; critical fixture scan exited 1 as designed, all artifact/compliance commands exited 0 | Covered by the same deterministic artifacts and full gate |
| Git tree | Detached exact commit; no tracked changes after gate | Detached exact commit; no tracked changes after gate |

Phase 2 additionally verifies canonical-root containment for every local path surface,
the guarded FastMCP 1.28.1 schema shim, per-key hosted rate limiting, the global hosted
judgment gate, safe key attribution, and three-way version agreement. The reusable
composite GitHub Action and fully green workflow burn-in are not claimed; they are Phase
3 scope. TypeScript analysis is 1.1 scope. Repository sharing, video upload, and Devpost
submission remain operator-only actions.
