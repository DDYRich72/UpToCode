# Current State

ArchAgent 0.1.0 is a Python-first static architecture scanner with 133 offline
tests, deterministic terminal/JSON/HTML reports, optional structured judgment,
approval-bound FIXPLAN generation, and five local stdio MCP tools.

The MVP is healthy but its public contracts are permissive, fingerprints are
line-based, diff auditing loses context, repository scanning is absent from MCP,
and hosted access, CI adoption, release automation, and a product site are not
implemented. The production program replaces those limitations with Report 2.0,
one bounded application service, typed MCP modes, stable baselines, SARIF,
trusted rulepacks, hosted isolation, and a dogfood compliance gate.

Deliberate bad fixtures and synthetic secret sentinels are test evidence, not
production exceptions. Production source currently has no findings but contains
one AA007 suppression; production 1.0 must remove it.
