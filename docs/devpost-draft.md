# Devpost Draft — Not Published

## Name

UpToCode

## Tagline

Evidence-backed architecture review for Python agents, from static findings to an approved Codex plan.

## Short description

UpToCode finds architecture-quality risks that ordinary syntax checks miss: unbounded execution, missing budgets, unsafe tool boundaries, absent validation, brittle resilience, missing evals, and weak observability. It combines conservative Python evidence with an opt-in GPT‑5.6 Structured Outputs judgment tier. Developers review findings before generating a non-mutating `FIXPLAN.md`; coding agents can call the same static checks over MCP.

## What it does

- Scans OpenAI Agents SDK, LangGraph, and recognizable custom Python loops.
- Produces terminal, versioned JSON, and standalone HTML reports with coverage and direct primary-source citations.
- Produces injection-safe GitHub workflow annotations, bounded job summaries, and no-null
  SARIF 2.1.0 with stable fingerprints for CI integrations.
- Ships a reusable composite GitHub Action that uploads SARIF before returning the
  scanner's preserved threshold exit code.
- Supports report baselines, changed-since scans, rule selection/ignores, and severity overrides.
- Redacts recognized secrets and narrow PII forms before output or optional judgment payloads.
- Records approvals/rejections in a report-bound manifest.
- Generates a Codex-ready implementation plan without changing source.
- Exposes ten typed local MCP tools spanning source/file/repository/diff audits, focused
  loop and schema checks, the rule catalog, review decisions, and FIXPLAN generation.
- Provides a live credential-protected hosted judge surface with eight submitted-content
  tools and no filesystem-path tools.
- Hardens hosted access with per-key in-memory rate limiting, a default-off global judgment
  gate, and payload-free short-digest attribution; local path tools share one resolved root.
- Audits its own production source at every release gate: zero findings, zero suppressions,
  and zero unexplained analysis warnings in the current verified build.

## How it was built

Codex collaborated throughout development: turning the specification into vertical slices,
building and reviewing the scanner, CLI, report formats, MCP surfaces, site, and tests, then
running clean-clone Windows and Linux release gates. UpToCode’s review workflow also emits
an approved-only, report-bound `FIXPLAN.md` designed as a safe Codex implementation hand-off.

The implementation uses Python 3.11+, AST-based evidence extraction, Pydantic contracts,
Typer, OpenAI Responses Structured Outputs with `gpt-5.6`, and the official Python MCP SDK.
GPT-5.6 is the optional double-consent judgment tier for bounded, redacted contextual
evidence. The offline gated build and cross-platform acceptance runner exercise the CLI,
real stdio and hosted MCP lifecycles, redaction, goldens, fixture non-mutation, and self-scan.

## Responsible behavior

Static analysis is offline. Judgment requires explicit code-sharing consent, sends bounded redacted evidence, disables storage, and preserves static results on failure. The repository has no source-changing auto-fix or automatic external action. Its optional network-reachable judge service remains protected by a separately distributed bearer key.

## Submission evidence

Sanitized captures are checked in under `docs/submission-evidence/`: the terminal bad-fixture
scan, standalone HTML report, redacted AA006 output, review manifest, approved-only FIXPLAN,
MCP `check_loop` response, acceptance PASS, and validation matrix. Exact private-clone judge
instructions are in the README. The Codex Session ID, public YouTube URL, repository sharing,
and hosted credential remain operator-only submission fields; the exact hosted endpoint and
no-paid-call testing procedure are documented in the repository.

## Current limitations

Version 1.0 analyzes Python, not TypeScript. It has no source-changing auto-fix, PR comment
bot or package publication. The local MCP has ten tools; live hosted mode
is a smaller bearer-authenticated submitted-content surface with a default 30-request/minute
per-key process-local limit. The composite Action supports source installation for the
private competition repository; semantic-version PyPI installation remains post-event.

This file is submission copy only. It does not authorize creating a Devpost entry, repository, upload, video, deployment, or package release.
