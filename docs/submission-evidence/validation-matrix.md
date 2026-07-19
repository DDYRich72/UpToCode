# Phase 1 Validation Matrix

Verified commit: `846c7f7` (`docs: prepare competition submission assets`). All model
calls were mocked/offline; no deployment, publication, key distribution, or submission
action occurred.

| Gate | Windows clean clone | Ubuntu/WSL clean clone |
|---|---|---|
| Runtime | Python 3.13.7; Node 22.19.0 | Python 3.13.12; Node 22.22.2 |
| `python -m pytest -q` | PASS — 158 | PASS — 158 |
| `python scripts/acceptance.py` | PASS — 158 tests, real stdio 10-tool probe and AA001 response | PASS — same |
| `python scripts/compliance.py` | PASS — zero production findings, warnings, suppressions | PASS — same |
| Ruff | PASS | PASS |
| strict mypy | PASS — 29 source files | PASS — 29 source files |
| branch coverage | PASS — 86% | PASS — 86% |
| clean `npm ci` | PASS — 506 packages; one non-fatal optional nested-WASM cleanup warning | PASS — 507 packages |
| site production build | PASS — `/`, `/connect` | PASS — `/`, `/connect` |
| rendered site tests | PASS — 2 | PASS — 2 |
| offline demo dry-run | PASS on exact commit; critical fixture scan exited 1 as designed, all artifact/compliance commands exited 0 | Covered by the same deterministic artifacts and full gate |
| Git tree | Detached exact commit; no tracked changes after gate | Detached exact commit; no tracked changes after gate |

The reusable composite GitHub Action and fully green workflow burn-in are not claimed;
they are Phase 3 scope. TypeScript analysis is 1.1 scope. The Codex Session ID, repository
sharing, video upload, and Devpost submission remain operator-only fields/actions.
