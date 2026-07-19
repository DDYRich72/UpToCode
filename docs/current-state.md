# Current State

ArchAgent 1.0.0 is a Python-first architecture-quality scanner with 167 offline
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

The Phase 2 implementation is submission-ready locally as candidate
`v1.0.0-rc3`: Windows and Ubuntu/WSL clean clones pass 167 tests, offline
acceptance and compliance, Ruff, strict mypy, 87% branch coverage, clean site
installs, production builds, and both rendered routes. The reusable composite
Action and fully green CI burn-in remain Phase 3 scope; no public hosted service
or published package is claimed.

Deliberate bad fixtures and synthetic secret sentinels are test evidence, not
production exceptions. The production compliance scan has zero findings,
warnings, or suppressions.
