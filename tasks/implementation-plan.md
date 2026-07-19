# Implementation Plan

## Gate 1

- [x] Package/import smoke test.
- [x] Public Pydantic contracts and deterministic serialization.
- [x] Config, discovery, exclusions, `.gitignore`, size limit, suppressions.
- [x] Redaction boundary.
- [x] AA001 evidence extraction and rule behavior.
- [x] JSON reporter, scan CLI, exit codes 0/1/2.
- [x] Record Gate 1 validation.

## Gate 2

- [x] Implement static AA002, AA003, AA004, AA006, AA007, AA010, AA011, AA012.
- [x] Implement judgment candidate extraction for AA003, AA005, AA008, AA009, AA010, AA011.
- [x] OpenAI Agents SDK, LangGraph, custom-loop, and raw-call evidence.
- [x] Rule registry/YAML, terminal reporter, fixtures, goldens, coverage and warnings.
- [x] Record Gate 2 validation.

## Gate 3

- [x] Mocked GPT-5.6 structured judgment and failure behavior.
- [x] Review manifest and FIXPLAN generation.
- [x] Standalone HTML report and automated structural verification.
- [x] Static MCP tools and integration tests.
- [x] Record Gate 3 validation (rendered visual inspection deferred to final validation).

## Gate 4

- [x] README and demo/submission drafts.
- [x] Cross-platform `scripts/acceptance.py`.
- [x] Self-scan triage.
- [x] Full completion audit and validation report.
- [x] Ask for approval, then run one live GPT-5.6 smoke test.

## Definition of Done mapping

- [x] All completed active gate criteria are recorded in `tasks/validation-report.md`.
- [x] Full offline suite passes.
- [x] Bad/clean fixtures and temporary review/plan flow pass without canonical source mutation.
- [x] Standalone HTML opened and visually inspected; user approved it and automated semantics pass.
- [x] MCP process integration and malformed-call survival pass.
- [x] Self-scan findings and analysis gaps are triaged in `PROGRESS.md`.
- [x] One explicitly authorized live GPT-5.6 smoke test passes before submission.
- [x] README and demo claims match the committed and validated Python surface.
- [x] No public repository, sharing, video, submission, package, deployment, or other external action has occurred.

Stretch TypeScript and GitHub output are inactive and are not part of the active Definition of Done. Judgment-enabled MCP arguments are present behind the same explicit code-sharing boundary; static MCP remains the default.

## Production 1.0 / Report 2.0

- [x] Strict Report 2.0 contracts, rule-result states, stable content fingerprints, metadata, usage, and Report 1.0 read compatibility.
- [x] Unified-diff reconstruction, JSON Schema 2020-12 validation, project evidence resolution, pruned nested-ignore discovery, baselines, and SARIF.
- [x] Single-file/directory CLI, module/version execution, changed-since, selectors, excludes, severity overrides, warning gates, and GitHub output.
- [x] Versioned trusted local rulepacks and production removal of the AA007 suppression.

## Reference MCP and hosted service

- [x] One `AuditService` pipeline shared by CLI, MCP, reporters, review, and planning.
- [x] Local stdio capability set with canonical workspace containment and workspace-based diff reconstruction.
- [x] Hosted submitted-content-only capability set, bearer authorization, strict limits, no path tools, health/readiness, and FastMCP lifecycle.
- [x] Official MCP client lifecycle tests for stdio and Streamable HTTP.
- [x] Non-root container, Cloud Run service template, release workflow, SBOM/provenance hooks, and rollback/operations documentation.

## Product access and release evidence

- [x] Functional landing, rules/privacy/install content, and `/connect` Codex configuration generator.
- [x] AA001–AA012 architecture matrix, ADRs, executable compliance artifact, zero-finding production dogfood gate, Ruff, strict mypy, coverage, and wheel build.
- [x] Site build and rendered-page tests for desktop/mobile-capable responsive routes on the local Windows environment.
- [ ] Container build (Docker is unavailable in the local environment; CI gate is configured).
- [ ] Explicitly approved publication/deployment and post-deploy synthetic smoke.
