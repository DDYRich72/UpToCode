# Feature Spec: TypeScript Analysis

Status: approved for Batch 2 implementation on 2026-07-20.

## Purpose

Extend UpToCode's evidence-backed architecture checks to TypeScript agent applications
without reusing Python AST heuristics or silently claiming unsupported rule coverage.

## User story

As an agent application developer, I want one local scan across Python and TypeScript so
that framework controls and coverage gaps are reported through the same review workflow.

## Scope

### In scope

- `.ts`, `.tsx`, and `.mts` discovery using the existing limits and exclusions.
- `tree-sitter` plus `tree-sitter-typescript`; no Node runtime and no regex parser.
- AA001, AA002, AA004, AA007, and AA012 evidence described in Batch 2.
- Report 2.2 per-language coverage and synchronized CLI, reporters, review, and MCP.
- Mixed-language fixtures, deliberate goldens, syntax recovery, and unsupported warnings.

### Out of scope

- JavaScript files, source rewriting, semantic type checking, package-resolution, or a
  TypeScript-specific rule engine.
- Judgment rules and static rules not listed above; these are explicitly not applicable.

## Public contracts

- `Coverage.language_coverage[]` contains language, discovered/analyzed files, stable and
  experimental rules evaluated, and rules not applicable.
- Top-level coverage remains the aggregate compatibility view.
- Report schema is `2.2`; ReviewManifest remains `2.0` and binds to Report 2.2.
- MCP source, file, repository, and diff tools accept `.py`, `.ts`, `.tsx`, and `.mts`.

## Risks and safety checks

- Parser errors preserve recovered evidence and emit `TYPESCRIPT_PARSE_RECOVERY`.
- Dynamic bounds emit warnings, not clean results.
- All scans remain offline; source is redacted before report or judgment egress.

## Acceptance criteria

- [ ] Wheel compatibility passes the 3.11-3.13 x Windows/macOS/Ubuntu CI matrix after the
  operator pushes the implementation branch; the matrix probe is committed and local
  Python 3.13/Windows installation is verified.
- [x] Mixed repositories report strict per-language evaluated/not-applicable coverage.
- [x] Supported TypeScript constructs retain file/line evidence and stable fingerprints.
- [x] CLI, JSON, terminal, HTML, GitHub, SARIF, review, FIXPLAN, and MCP remain synchronized.
- [x] Bad and clean TypeScript fixtures, suppression, syntax recovery, and false-positive
  regressions are covered by offline tests.
