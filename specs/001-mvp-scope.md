# MVP Scope

## Purpose

Deliver the Python-first ArchAgent architecture-quality scanner defined by `SPEC.md` before the Build Week deadline.

## User story

As an agent developer, I want evidence-backed architecture findings and explicit coverage gaps so I can approve reliable remediation plans before changing code.

## Acceptance

- All committed surfaces and AA001–AA012 behavior match `SPEC.md`.
- Offline tests and cross-platform acceptance pass.
- Static scans make no network calls and secrets remain redacted.
- Review and planning are non-mutating.
- Validation maps every active Definition of Done item to evidence.

## Non-goals

Instruction-file linting, runtime tracing service, auto-fix, and unapproved external actions.

