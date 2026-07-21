# Current State

The working 1.11.0 Batch 4.1 source adds a persistent pygls server and VS Code language
client for file-scoped Python and TypeScript diagnostics. Open/save scans share the CLI's
`AuditService`, discard stale versions, remain offline, and perform no workspace indexing.
Explicit code actions can open the registry citation or matching FIXPLAN fingerprint and,
after metadata validation and user confirmation, insert one structured suppression without
auto-saving. Release tags, publication, and deployment remain operator-gated.

UpToCode 1.0.0 is a Python-first architecture-quality scanner with 188 offline
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

Phase 2 is preserved remotely as `v1.0.0-rc3`. Phase 3 is preserved remotely as
`v1.0.0-rc4` at corrected commit `4fe8a61`; it adds a
nine-cell Python matrix, isolated wheel dependency audit, site lint/type/build
gates, container lifecycle smoke, SHA-pinned Actions, retained validation
artifacts, weekly Dependabot, injection-safe GitHub annotations, bounded Markdown
summaries, hardened SARIF, and a reusable upload-before-fail composite Action.
The rc4 release candidate passes 175 tests, acceptance and compliance, Ruff, strict mypy,
88% branch coverage, isolated wheel audit, and site lint/type/build tests. GitHub
run `29703827878` was the first full burn-in; exact rc4 tag run `29706598903` also
passed all nine
Python/OS cells plus the package/site, isolated wheel-audit, and container lifecycle jobs.

Phase 4 is preserved remotely as `v1.0.0-rc5` at `752bb02`. It removes the unused
Drizzle/D1 starter surface, safely updates
the direct Cloudflare/Vite and framework patch dependencies, and documents the remaining
Next/PostCSS advisory risk. The site remains exactly `/` and `/connect`, defaults to honest
local setup, uses an explicit hosted placeholder, and now has keyboard tabs, visible focus,
skip navigation, reduced-motion handling, and responsive desktop/mobile evidence. Fresh
Windows and Ubuntu/WSL clones pass five site tests and the complete release gate. Branch
CI `29710990279`, tag CI `29710992278`, and release-artifact run `29710992277` passed.

Phase 5 deployed a credential-protected pre-production judge MCP to Cloud Run in
`us-central1`. The immutable submission tag records its exact superseded resource names;
its revision was pinned to image digest
`sha256:298fadd434cafc4a28182a4f263ca1a2b23c2aea0d02627ac9aebe3046bd778d`, exposes eight
submitted-content tools, and passed live readiness, unauthorized-access, AA001,
judgment-gate, rate-limit, and payload-free-log checks. Hosted judgment remains off, no
OpenAI key is attached, and the live test made zero paid model calls. The raw judge key is
kept outside the repository for private submission notes; it has not been distributed.
It is not the UpToCode production endpoint. Phase 5 is preserved remotely
as `v1.0.0-rc6` at `f578f24`. That exact commit passes the
complete Windows and Ubuntu/WSL submission gate: 186 tests, acceptance, compliance, Ruff,
strict mypy, 88% branch coverage, clean site install/lint/type/build/tests, offline demo,
and clean trees. Branch CI `29717585938`, tag CI `29717587213`, and release-artifact run
`29717587195` also pass on the exact rc6 commit.

Deliberate bad fixtures and synthetic secret sentinels are test evidence, not
production exceptions. The production compliance scan has zero findings,
warnings, or suppressions.

Phase 7 completed on `codex/uptocode-production`. Every current tracked surface uses the
UpToCode identity: distribution/import/CLI `uptocode`, `UPTOCODE_*` settings,
`io.github.DDYRich72/uptocode` registry metadata, and deployed `uptocode-mcp` resources.
The production endpoint is
`https://uptocode-mcp-1015314816960.us-central1.run.app/mcp`; its immutable revision passed
the no-paid-call hosted control and log-safety checks. The public repository defaults to
`codex/uptocode-production`; `uptocode==1.0.0` is published on PyPI through the protected
GitHub OIDC environment with verified provenance; and the official MCP Registry lists
active latest server `io.github.DDYRich72/uptocode` version `1.0.0`.
