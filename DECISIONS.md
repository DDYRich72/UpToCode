# Decisions

## D001 — Pre-production naming decision (superseded)

The original naming decision is preserved in Git history. D008 is the only current naming
authority and defines the UpToCode production identity.

## D002 — Time policy

The current date is Saturday, July 18, 2026. Stretch work remains gated behind Gate 3 and the Monday noon cut policy.

## D003 — Offline implementation

The OpenAI integration will be implemented and verified with mocks before any live API call. Live use requires explicit approval.

## D004 — Rule-slice test expectations

Gate 1 AA001 tests originally asserted the entire report contained only AA001. Once Gate 2 legitimately added project-level AA011/AA012 findings, those assertions no longer isolated the behavior named by the tests. They now assert specifically on AA001 while Gate 2 fixture tests own whole-report expectations.

## D005 — Firestore access-control plane deferred to 1.1 (2026-07-19)

The proposed Firestore-backed beta-access system (public access-request endpoint, stored contact PII, key lifecycle records, transactional quotas, admin tooling, GCP provisioning) is deferred to 1.1. It was never part of the shipped program, its absence does not impede production readiness at manually provisioned private-beta scale, and judges receive credentials directly, so the flow is invisible to judging. 1.0 ships the minimal hosted controls instead: in-memory per-key rate limiting, an `UPTOCODE_HOSTED_JUDGMENT` gate defaulting off, and safe key-prefix log attribution, on top of the existing `UPTOCODE_API_KEY_HASHES` allowlist. Operator delegated this call; no Firestore code lands in 1.0 and no spec may record it as approved 1.0 scope.

## D006 — Submission via private repository; publication decoupled (2026-07-19)

Per the official rules (https://openai.devpost.com/rules), the submission repository may be private if shared with `testing@devpost.com` and `build-week-event@openai.com`. UpToCode submits that way. PyPI publication, MCP registry submission, and the package-name recheck are post-event work and no longer gate the submission.

## D007 — Always submission-ready (2026-07-19)

Every phase in `tasks/completion-plan-v2.md` must exit through the Submission-Ready Gate: full offline suite, acceptance, compliance, lint, strict typing, coverage floor, site tests, claims exactly matching the shipped surface, a successful demo dry-run, a clean tree, and a tagged release candidate. If the deadline arrives mid-phase, the previous tag is submitted as-is.

## D008 — UpToCode is the canonical production identity (2026-07-20)

The operator directed that every current association with the program and MCP use the
name **UpToCode**. D008 supersedes D001 for all post-submission development; the immutable
submission tag and Git history remain historical evidence and are not rewritten.

The first public production release uses `uptocode` for the PyPI distribution, Python
import package, CLI, configuration/output paths, and local MCP registration key;
`UPTOCODE_*` for environment variables; `io.github.DDYRich72/uptocode` for the official
MCP Registry server name; and `uptocode-mcp` for hosted resources. The AA001–AA012 rule
identifiers remain stable because they are versioned report-contract identifiers, not a
product-name abbreviation. No legacy-branded public alias is published because the prior
distribution was never released to PyPI.

## D009 — Batch 2 TypeScript implementation approved (2026-07-20)

The operator's instruction to implement the approved Batch 2 plan is the explicit gate
for `specs/005-typescript-analysis.md`. TypeScript uses tree-sitter, adds no Node runtime,
and feeds the existing normalized evidence and AA rule pipeline. Report 2.2 adds strict
per-language coverage; ReviewManifest remains 2.0.

## D010 — LlamaIndex is the fourth Python adapter (2026-07-20)

The implementation-time PyPI Stats comparison selected LlamaIndex: approximately
7,189,570 downloads in the prior month versus 609,455 for PyAutoGen and 634,739 for AG2.
The fourth adapter therefore targets current LlamaIndex agents and workflows. Counts are
a dated prioritization signal, not a product quality claim.
