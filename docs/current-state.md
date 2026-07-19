# Current State

ArchAgent 1.0.0 is a Python-first architecture-quality scanner with 175 offline
tests, deterministic terminal/JSON/HTML/GitHub/SARIF reports, optional GPT-5.6
Structured Outputs judgment, approval-bound FIXPLAN generation, and ten local
stdio MCP tools.

Report 2.0, stable fingerprints and baselines, contextual diff auditing,
repository scanning, strict typed MCP contracts, trusted rulepacks, the hosted
submitted-content subset, and the dogfood compliance gate are implemented. The
local server resolves one canonical workspace root at startup and contains every
path-bearing tool to it. Hosted access has bearer authorization, bounded per-key
in-memory rate limiting, default-off global judgment, safe digest-prefix log
attribution, payload limits, and temporary-directory cleanup.

Phase 2 is preserved remotely as `v1.0.0-rc3`. The Phase 3 candidate adds a
nine-cell Python matrix, isolated wheel dependency audit, site lint/type/build
gates, container lifecycle smoke, SHA-pinned Actions, retained validation
artifacts, weekly Dependabot, injection-safe GitHub annotations, bounded Markdown
summaries, hardened SARIF, and a reusable upload-before-fail composite Action.
The local candidate passes 175 tests, acceptance and compliance, Ruff, strict
mypy, 88% branch coverage, isolated wheel audit, and site lint/type/build tests.
The first fully green GitHub burn-in remains pending and is not claimed. No public
hosted service or published package is claimed.

Deliberate bad fixtures and synthetic secret sentinels are test evidence, not
production exceptions. The production compliance scan has zero findings,
warnings, or suppressions.
