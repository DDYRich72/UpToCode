# Decisions

## D001 — Product and executable names

Product name is ArchAgent. The Python package is `archagent_audit` and CLI is `archagent-audit` because the bare `archagent` command is already in active use.

## D002 — Time policy

The current date is Saturday, July 18, 2026. Stretch work remains gated behind Gate 3 and the Monday noon cut policy.

## D003 — Offline implementation

The OpenAI integration will be implemented and verified with mocks before any live API call. Live use requires explicit approval.

## D004 — Rule-slice test expectations

Gate 1 AA001 tests originally asserted the entire report contained only AA001. Once Gate 2 legitimately added project-level AA011/AA012 findings, those assertions no longer isolated the behavior named by the tests. They now assert specifically on AA001 while Gate 2 fixture tests own whole-report expectations.
