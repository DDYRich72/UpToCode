# Feature Spec: UpToCode 1.1 TypeScript Analysis

Status: deferred; specification only. No TypeScript analyzer ships in 1.0.

## Purpose

Extend UpToCode's evidence-backed architecture checks to TypeScript agent applications
without pretending Python AST heuristics transfer across languages.

## Scope

### In scope for a separately approved 1.1 implementation

- A real TypeScript parser with source ranges and syntax-error recovery.
- Framework adapters for the OpenAI Agents SDK and recognizable custom agent loops.
- Explicit per-language applicability for every AA001–AA012 rule and subcheck.
- Shared language-neutral evidence contracts where semantics genuinely align.
- TypeScript fixtures, goldens, coverage accounting, CLI selection, and MCP results.

### Out of scope

- Regex-only parsing or silent reuse of Python evidence rules.
- Claiming rule coverage where TypeScript semantics are unsupported.
- Source-changing auto-fix.

## Acceptance criteria for future implementation

- [ ] Parser choice and dependency/security review are approved.
- [ ] Each rule declares supported, judgment-only, or not-applicable status by language.
- [ ] Findings retain exact file/range evidence and stable fingerprints.
- [ ] Mixed Python/TypeScript repositories report per-language coverage truthfully.
- [ ] CLI, JSON, HTML, SARIF, review, FIXPLAN, and MCP contracts remain synchronized.
