# Phase 3 Validation Matrix

Verified implementation commit: `790ef5d` (`fix(ci): group dependency updates`). GitHub
run `29703827878` passed all 12 jobs. All model calls were mocked/offline; no deployment,
publication, key distribution, or submission action occurred.

| Gate | Windows clean clone | Ubuntu/WSL clean clone |
|---|---|---|
| Runtime | GitHub Python 3.11/3.12/3.13; local Node 24.14.1 | Python 3.12.3; Node 22.22.2 |
| `python -m pytest -q` | PASS — 175 in every Windows matrix cell | PASS — 175 |
| `python scripts/acceptance.py` | PASS — every Windows matrix cell | PASS — 175 tests, real stdio 10-tool probe and AA001 response |
| `python scripts/compliance.py` | PASS — zero production findings, warnings, suppressions; version contract synchronized at 1.0.0 | PASS — same |
| Ruff | PASS | PASS |
| strict mypy | PASS — 30 source files in every Windows matrix cell | PASS — 30 source files |
| branch coverage | PASS — 88% in every Windows matrix cell | PASS — 88% |
| clean `npm ci` | PASS — 507 packages | PASS — 508 packages |
| site lint / `tsc --noEmit` | PASS | PASS |
| site production build | PASS — `/`, `/connect` | PASS — `/`, `/connect` |
| rendered site tests | PASS — 2 | PASS — 2 |
| offline demo dry-run | Covered by the same deterministic WSL artifacts | PASS; critical scan exited 1 as designed and artifact commands exited 0 |
| Git tree | Clean after generated type-check artifact removal | Clean after generated demo/type-check artifact removal |

The GitHub run independently passed 175 tests, acceptance, compliance, Ruff, strict mypy,
and 88% branch coverage in every Python/OS cell. It also passed the isolated installed-wheel
audit, package/SBOM/SARIF/site job, and container health/auth/shutdown job. TypeScript
analysis remains 1.1 scope; the Phase 3 site-only `tsc --noEmit` check does not change that
claim. Repository sharing, video upload, and Devpost submission remain operator-only.
