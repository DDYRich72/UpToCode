# Devpost Draft — Not Published

## Name

ArchAgent

## Tagline

Evidence-backed architecture review for Python agents, from static findings to an approved Codex plan.

## Short description

ArchAgent finds architecture-quality risks that ordinary syntax checks miss: unbounded execution, missing budgets, unsafe tool boundaries, absent validation, brittle resilience, missing evals, and weak observability. It combines conservative Python evidence with an opt-in GPT‑5.6 Structured Outputs judgment tier. Developers review findings before generating a non-mutating `FIXPLAN.md`; coding agents can call the same static checks over MCP.

## What it does

- Scans OpenAI Agents SDK, LangGraph, and recognizable custom Python loops.
- Produces terminal, versioned JSON, and standalone HTML reports with coverage and direct primary-source citations.
- Redacts recognized secrets and narrow PII forms before output or optional judgment payloads.
- Records approvals/rejections in a report-bound manifest.
- Generates a Codex-ready implementation plan without changing source.
- Exposes ten typed local MCP tools spanning source/file/repository/diff audits, focused
  loop and schema checks, the rule catalog, review decisions, and FIXPLAN generation.
- Provides a separate hosted submitted-content surface with no filesystem-path tools.

## How it was built

Python 3.11+, AST-based evidence extraction, Pydantic contracts, Typer, OpenAI Responses Structured Outputs with `gpt-5.6`, and the official Python MCP SDK. The gated build and cross-platform acceptance runner exercise the CLI workflow, real stdio and hosted MCP lifecycles, redaction, goldens, fixture non-mutation, and self-scan.

## Responsible behavior

Static analysis is offline. Judgment requires explicit code-sharing consent, sends bounded redacted evidence, disables storage, and preserves static results on failure. The repository has no source-changing auto-fix, public service, or automatic external action.

## Evidence to capture after approval

- Terminal scan of `fixtures/bad_python`.
- Standalone HTML header, coverage panel, bar chart, and one finding.
- Redacted AA006 excerpt.
- Review manifest and approved-only `FIXPLAN.md`.
- MCP `check_loop` AA001 response.
- Acceptance runner PASS line and final validation matrix.

This file is submission copy only. It does not authorize creating a Devpost entry, repository, upload, video, deployment, or package release.
