# Anthropic / Claude Framework Contract

Inspected 2026-07-20 against the public Claude tool-use documentation.

## Recognized contract

- `client.messages.create(...)` and its `max_tokens`, `tools`, timeout, and retry configuration.
- The canonical client-tool loop continues while `stop_reason == "tool_use"`; any other
  stop reason leaves that loop. `end_turn` is semantic completion, while `max_tokens`,
  `stop_sequence`, and `refusal` require caller-specific handling.
- Server tools may return `pause_turn`; repeated continuations still require an outer cap.
- Tool dictionaries with `input_schema`, Agent SDK `@tool`, and `PreToolUse`/`PostToolUse`
  hook names provide tool provenance and enforcement evidence.

Text-parsed completion, dynamically dispatched clients, and numeric caps without the
structured stop protocol remain findings or coverage warnings.

## Primary sources

- https://platform.claude.com/docs/en/agents-and-tools/tool-use/how-tool-use-works
- https://platform.claude.com/docs/en/build-with-claude/handling-stop-reasons
- https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-runner
