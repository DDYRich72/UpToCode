# UpToCode Project Constitution

## Product

- Name: UpToCode
- Package: `uptocode`
- CLI: `uptocode`
- Build type: Python developer tool

## Mission

Help developers find architecture-quality failures in Python agent applications before production, while distinguishing proven findings from analysis gaps.

## Users

- Primary: developers and architects building agent applications.
- Secondary: reviewers and coding agents consuming JSON, HTML, or MCP results.

## Production contract

### Must have

- Python scanning for OpenAI Agents SDK, LangGraph, raw OpenAI calls, and recognizable custom loops.
- AA001–AA013 static/judgment behavior defined by `SPEC.md`.
- Terminal, JSON, standalone HTML, review manifest, FIXPLAN generation, and static MCP tools.
- Offline-by-default scanning, coverage warnings, suppression handling, and irreversible secret redaction.
- One bounded, typed audit pipeline shared by the CLI, local MCP, hosted MCP, review, and planning.
- Report 2.1 rule outcomes that distinguish pass, finding, suppression, uncertainty, failure, and non-applicability.
- A dogfood gate: production source has zero findings, zero suppressions, and zero unexplained warnings.
- A stateless hosted MCP surface that accepts submitted content only and never reads arbitrary filesystem paths.

### Later

- TypeScript adapter, GitHub Actions output, and judgment-enabled MCP calls after Gate 3.

### Out of scope

- Instruction-file linting, runtime observability service, source-changing auto-fix, public deployment, and unapproved paid API use.

## Success criteria

The active Definition of Done is proven by `tasks/validation-report.md` and
`.uptocode/architecture-compliance.json`. Every AA001-AA013 control has
an implementation reference, a test reference, and a passing result.

## Stack

- Python 3.11+, `ast`, Pydantic, Typer, Rich, PyYAML, PathSpec, OpenAI Python SDK, official Python MCP SDK, and pytest.
- Sites for the public landing/connect surface and a containerized ASGI/FastMCP service for hosted transport.

## Privacy and safety

- Static work is offline.
- Judgment requires `--judgment --send-code` and sends only bounded redacted excerpts.
- Never publish, deploy, submit, message externally, or incur API cost without approval.
- Never mutate scanned source in v1.
- Treat submitted source, diffs, configuration, model output, and external rulepacks as untrusted inputs.
- Hosted mode never loads path rulepacks, scans server-local paths, or persists submitted code.

## Agent guardrails

- Build only approved scope.
- Preserve positive evidence and uncertainty.
- Update specs before changing public behavior.
- Verify each gate before advancing.
- Production suppressions are prohibited; fix the implementation or improve the analyzer.
