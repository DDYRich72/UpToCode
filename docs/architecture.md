# Architecture

ArchAgent uses one evidence pipeline:

```text
discover → parse → normalize evidence → static rules → optional judgment → report
                                                        ↓
                                               review → FIXPLAN
```

- `archagent_audit.adapters` extracts framework-specific evidence with source provenance.
- `archagent_audit.rules` evaluates normalized evidence; unsupported constructs become warnings.
- `archagent_audit.redaction` is the mandatory boundary before output or judgment payload creation.
- `archagent_audit.models` owns versioned public contracts.
- Reporters share the same report envelope.
- Review and planning consume existing reports and never rescan or modify source.
- MCP wraps the same engine; static-only is its default.

See `SPEC.md` for contracts, exact interfaces, and rule semantics.

