# Architecture Compliance

| Rule | ArchAgent production invariant | Implementation evidence | Automated evidence |
|---|---|---|---|
| AA001 | File, rule, judgment, and request execution are finite, deadline-aware, and preserve partial results. | `config.py`, `engine.py`, `judgment.py`, Cloud Run timeout | `test_gate2_edges.py`, `test_production_contract.py` |
| AA002 | Typed policies cap file, aggregate source, request, output, rule-call, elapsed-time, per-key hosted request rate, and hosted concurrency usage. | `ScanConfig`, `JudgmentConfig`, MCP byte limits/token buckets, Cloud Run concurrency | `test_gate2_edges.py`, `test_mcp_hardening.py`, `test_production_contract.py` |
| AA003 | Analysis is read-only; publication, deployment, paid calls, baseline replacement, and trusted plugins require operator action. | review/FIXPLAN services, protected release environment, trusted rulepack loader | `test_review_plan.py`, `test_production_contract.py` |
| AA004 | Configuration, paths, diffs, schemas, MCP requests, and reports are strictly validated. | strict Pydantic models, single-root containment, guarded FastMCP schema contract, diff reconstructor, Draft 2020-12 validator | `test_mcp_hardening.py`, `test_production_contract.py`, `test_gate2_edges.py` |
| AA005 | Submitted code is delimited untrusted data and cannot alter judgment policy or trusted metadata. | system/user judgment separation and normalized redacted candidate payload | `test_judgment_candidates.py`, `test_judgment.py` |
| AA006 | Sensitive values are redacted before report, judgment, or log egress. | `redaction.py`, payload-free hosted middleware and operations policy | `test_gate1.py`, `test_judgment.py`, `test_rule_contract_matrix.py` |
| AA007 | Timeouts and bounded replay-safe retries preserve partial static results; authentication and validation failures are not retried. | configured OpenAI client/Responses options and typed error mapping | `test_judgment.py`, production dogfood scan |
| AA008 | One `AuditService` pipeline is used; no agent framework or unnecessary orchestration exists. | `AuditService`, CLI/MCP adapters, ADR 0001/0003 | `test_production_contract.py` import-boundary gate |
| AA009 | MCP tools have purpose-specific strict schemas, descriptions, structured outputs, annotations, and actionable errors. | guarded FastMCP typed tools and rule resource | `test_mcp_hardening.py`, `test_mcp_server.py`, `test_hosted_lifecycle.py` |
| AA010 | Model output is domain-validated and cannot control rule metadata or side effects. | `JudgmentBatch`, trusted registry merge, non-mutating review/plan | `test_judgment.py`, `test_review_plan.py` |
| AA011 | Every rule and public transport has positive, clean, adversarial, unsupported, and regression coverage. | rule matrix, official-client stdio/HTTP acceptance, cross-platform CI | `test_rule_contract_matrix.py`, `test_hosted_lifecycle.py`, `scripts/acceptance.py` |
| AA012 | Payload-free timing, counts, safe key attribution, error classes, model usage, synchronized versions, and correlation-capable MCP requests exist at boundaries. | Report metadata/usage, MCP lifecycle logs, version contract, operations policy | `test_gate1.py`, `test_judgment.py`, `test_mcp_hardening.py`, `test_hosted_lifecycle.py` |

`scripts/compliance.py` scans only production Python source and emits
`.archagent-audit/architecture-compliance.json`. It fails on any production
finding, suppression, unexplained warning, or package/runtime/server version mismatch. The release workflow includes that
artifact in the provenance-attested release subject set; narrative evidence alone
cannot mark a rule passed.
