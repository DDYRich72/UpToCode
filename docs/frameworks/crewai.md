# CrewAI Framework Contract

Inspected 2026-07-20 against CrewAI 1.14.6 public documentation.

## Recognized contract

- `Agent(max_iter=...)` controls maximum agent iterations; the documented default is 20.
- `max_execution_time` is an optional seconds-based execution ceiling and
  `max_retry_limit` is the bounded retry control.
- `Crew(..., process=Process.sequential|Process.hierarchical)` and `kickoff()` identify
  execution and process topology.
- `@tool` provides tool provenance. Dynamic/YAML-only agent construction is not resolved
  by this static slice and must produce a coverage warning when recognizable.

## Primary sources

- https://docs.crewai.com/en/concepts/agents
- https://docs.crewai.com/en/concepts/processes
- https://docs.crewai.com/en/concepts/tools
