# PydanticAI Framework Contract

Inspected 2026-07-20 against the public PydanticAI API documentation.

## Recognized contract

- `Agent(...)` with `run`, `run_sync`, or `run_stream` identifies execution.
- `UsageLimits(request_limit=..., total_tokens_limit=...)` provides whole-run request and
  token-budget evidence when passed directly or through a statically resolved name.
- `ModelSettings` timeout/retry fields provide AA007 evidence when statically visible.
- `@agent.tool` and `@agent.tool_plain` provide tool provenance; function-body guards and
  Pydantic validation calls provide validation evidence.

Provider-specific settings, dynamically constructed limits, and custom toolsets outside
these forms are reported as inconclusive rather than clean.

## Primary sources

- https://pydantic.dev/docs/ai/api/pydantic-ai/usage/
- https://pydantic.dev/docs/ai/api/pydantic-ai/settings/
- https://pydantic.dev/docs/ai/tools/
