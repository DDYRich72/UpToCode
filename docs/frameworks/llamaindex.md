# LlamaIndex Framework Contract

Inspected 2026-07-20 against current public LlamaIndex agent/workflow documentation.

## Recognized contract

- `FunctionAgent`, `ReActAgent`, and `AgentWorkflow` identify current agent forms;
  `.run()` and `.chat()` identify execution.
- Statically visible `max_iterations` is iteration-bound evidence. Construction without a
  visible bound is inconclusive because current workflow variants do not share one proven
  default contract.
- `tools=[...]`, `output_cls=...`, `Memory.from_defaults(token_limit=...)`, and visible
  model timeout/retry/token options provide normalized tool, validation, and budget facts.
- Custom workflow subclasses and dynamic tool assembly remain unsupported with warnings.

## Primary sources

- https://docs.llamaindex.ai/en/latest/understanding/agent/structured_output/
- https://docs.llamaindex.ai/en/stable/examples/tools/order_completion_agent_with_artifact_editor/
- https://docs.llamaindex.ai/en/latest/examples/agent/agents_as_tools/
