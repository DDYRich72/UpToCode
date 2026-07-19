# ArchAgent FIXPLAN

Generated from explicitly approved findings.

## AA003: Ungated destructive action

Fingerprint: `8502169c0c07fcc71a5dbcb0`

### Objective

Require an explicit approval mechanism before execution.

### Evidence

- Location: `agent.py:11`
- Tool delete_user can change state without a recognized approval gate.

### Likely files

- `agent.py`

### Implementation steps

1. Inspect the cited location and its callers to confirm the evidence.
2. Implement the smallest change that satisfies: Require an explicit approval mechanism before execution.
3. Add a regression test for the observed failure and a clean counterpart.
4. Run the targeted test and the full project validation suite.

### Acceptance checks

- [ ] ArchAgent no longer emits AA003 at this location.
- [ ] The clean counterpart remains finding-free.
- [ ] Existing behavior and public contracts remain intact.

### Risks and tradeoffs

The control adds implementation and maintenance overhead.

### Codex prompt

```text
Address ArchAgent finding AA003 (8502169c0c07fcc71a5dbcb0) in agent.py:11. Observed: Tool delete_user can change state without a recognized approval gate. Required outcome: Require an explicit approval mechanism before execution. Preserve existing behavior, add regression coverage, run the relevant checks, and report evidence.
```

## AA001: Unbounded agent loop

Fingerprint: `d5e085372a107c27efaa8b1d`

### Objective

Set a turn cap and preserve partial results when the cap is reached.

### Evidence

- Location: `agent.py:21`
- while True has no exit

### Likely files

- `agent.py`

### Implementation steps

1. Inspect the cited location and its callers to confirm the evidence.
2. Implement the smallest change that satisfies: Set a turn cap and preserve partial results when the cap is reached.
3. Add a regression test for the observed failure and a clean counterpart.
4. Run the targeted test and the full project validation suite.

### Acceptance checks

- [ ] ArchAgent no longer emits AA001 at this location.
- [ ] The clean counterpart remains finding-free.
- [ ] Existing behavior and public contracts remain intact.

### Risks and tradeoffs

A cap can truncate legitimately long tasks.

### Codex prompt

```text
Address ArchAgent finding AA001 (d5e085372a107c27efaa8b1d) in agent.py:21. Observed: A custom while-True agent loop has no detectable exit. Required outcome: Set a turn cap and preserve partial results when the cap is reached. Preserve existing behavior, add regression coverage, run the relevant checks, and report evidence.
```
