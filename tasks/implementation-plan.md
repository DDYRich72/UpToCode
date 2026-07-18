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

- [ ] Mocked GPT-5.6 structured judgment and failure behavior.
- [ ] Review manifest and FIXPLAN generation.
- [ ] Standalone HTML report and visual verification.
- [ ] Static MCP tools and integration tests.
- [ ] Record Gate 3 validation.

## Gate 4

- [ ] README and demo assets.
- [ ] Cross-platform `scripts/acceptance.py`.
- [ ] Self-scan triage.
- [ ] Full completion audit and validation report.
- [ ] Ask for approval, then run one live GPT-5.6 smoke test.

## Definition of Done mapping

Each item in `SPEC.md §9` maps to the corresponding gate above; authoritative evidence is recorded in `tasks/validation-report.md`.
