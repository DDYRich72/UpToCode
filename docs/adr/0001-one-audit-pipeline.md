# ADR 0001: One Audit Pipeline

All interfaces call one application-level AuditService. Deterministic rules stay
pure; filesystem, diff, OpenAI, and rulepack behavior are adapters. This prevents
CLI/MCP drift and keeps budgets, redaction, and coverage semantics consistent.
