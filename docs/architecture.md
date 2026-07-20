# Architecture

UpToCode uses one evidence pipeline and inward-only dependency direction:

```text
discover → parse → normalize evidence → static rules → optional judgment → report
                                                        ↓
                                               review → FIXPLAN
```

- `uptocode.adapters` extracts framework-specific evidence with source provenance.
- `uptocode.rules` evaluates normalized evidence; unsupported constructs become warnings.
- `uptocode.redaction` is the mandatory boundary before output or judgment payload creation.
- `uptocode.models` owns versioned public contracts.
- `uptocode.rules.core.yml` owns severity, tier, maturity, and structured citations;
  evaluators never invent citation metadata.
- Reporters share the same report envelope.
- Review and planning consume existing reports and never rescan or modify source.
- Suppressions are parsed once per file, baselines classify debt before muting known
  findings, and share-safe rendering sanitizes a copied Report 2.1 envelope.
- MCP wraps the same engine; static-only is its default.

```text
interfaces (CLI, MCP, reporters)
              ↓
application (audit, review, plan, baseline)
              ↓
domain (evidence, findings, policies, rule outcomes)
              ↑
adapters (Python AST, filesystem, diff, OpenAI, rulepacks)
```

Public boundaries use strict Pydantic contracts. Domain and deterministic rule
evaluation perform no filesystem or network access. `AuditService` owns scan
budgets, deadlines, cancellation, and report assembly. Local MCP may read only
inside its configured root; hosted MCP registers no path-bearing tools.

Raw source is untrusted data. It is bounded before parsing and irreversibly
redacted before report, judgment, or log egress. Judgment can supply reasoning
only; registry metadata remains authoritative.

See `SPEC.md` for contracts, exact interfaces, and rule semantics.
