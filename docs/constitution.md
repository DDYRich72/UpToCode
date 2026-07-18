# ArchAgent Project Constitution

## Product

- Name: ArchAgent
- Package: `archagent_audit`
- CLI: `archagent-audit`
- Build type: Python developer tool

## Mission

Help developers find architecture-quality failures in Python agent applications before production, while distinguishing proven findings from analysis gaps.

## Users

- Primary: developers and architects building agent applications.
- Secondary: reviewers and coding agents consuming JSON, HTML, or MCP results.

## MVP

### Must have

- Python scanning for OpenAI Agents SDK, LangGraph, raw OpenAI calls, and recognizable custom loops.
- AA001–AA012 static/judgment behavior defined by `SPEC.md`.
- Terminal, JSON, standalone HTML, review manifest, FIXPLAN generation, and static MCP tools.
- Offline-by-default scanning, coverage warnings, suppression handling, and irreversible secret redaction.

### Stretch

- TypeScript adapter, GitHub Actions output, and judgment-enabled MCP calls after Gate 3.

### Out of scope

- Instruction-file linting, runtime observability service, source-changing auto-fix, public deployment, and unapproved paid API use.

## Success criteria

The active Definition of Done in `SPEC.md` is proven by `tasks/validation-report.md`.

## Stack

- Python 3.11+, `ast`, Pydantic, Typer, Rich, PyYAML, PathSpec, OpenAI Python SDK, official Python MCP SDK, and pytest.

## Privacy and safety

- Static work is offline.
- Judgment requires `--judgment --send-code` and sends only bounded redacted excerpts.
- Never publish, deploy, submit, message externally, or incur API cost without approval.
- Never mutate scanned source in v1.

## Agent guardrails

- Build only approved scope.
- Preserve positive evidence and uncertainty.
- Update specs before changing public behavior.
- Verify each gate before advancing.

