# ArchAgent

ArchAgent is a design-time architecture-quality scanner for Python agent applications. It finds missing execution bounds, run budgets, approvals, validation, resilience controls, evals, and observability; explains the evidence; and produces an approval-driven plan for Codex without rewriting source code.

The product is deliberately narrower than a general agent-security scanner. Version 1.0 recognizes OpenAI Agents SDK patterns, LangGraph limits, and conservative custom Python agent loops. Static scans are local and offline. Optional GPT‑5.6 judgment is explicit, bounded, redacted, and code-sharing gated.

> The Python distribution and command are `archagent-audit`; the import package is `archagent_audit`. The bare `archagent` name already has active uses. Registry and trademark availability must be rechecked before any publication.

## Install locally

ArchAgent requires Python 3.11 or newer. This repository has not been published as a package.

```text
python -m pip install -e ".[test]"
archagent-audit --help
```

All ordinary tests are mocked/offline:

```text
python -m pytest -q
python scripts/acceptance.py
```

## Scan, review, plan

```text
archagent-audit scan PATH [--format terminal|json|html|github|sarif] [--output FILE]
                         [--judgment --send-code]
                         [--fail-on critical|warning|info]
                         [--baseline FILE|--update-baseline FILE]
                         [--changed-since REF] [--select RULES] [--ignore RULES]
                         [--exclude GLOB] [--severity RULE=LEVEL]
                         [--fail-on-analysis-warning] [--verbose]
archagent-audit review REPORT [--approve IDS|--approve-all] [--reject IDS]
                              [--reuse MANIFEST] [--non-interactive]
archagent-audit plan REPORT --manifest MANIFEST [--output FIXPLAN.md]
archagent-audit serve --transport stdio --root PATH
archagent-audit serve --transport streamable-http --mode hosted
```

The v1 workflow is non-mutating:

```text
archagent-audit scan . --format json --output report.json
archagent-audit review report.json --approve AA001,AA003 --reject AA012 --non-interactive
archagent-audit plan report.json --manifest .archagent-audit/manifest.json --output FIXPLAN.md
```

`review` binds decisions to the exact report fingerprint. `plan` refuses a mismatched manifest and includes only approved findings. Neither command edits the scanned repository.

Exit codes are `0` for no configured threshold breach, `1` for a finding at or above `--fail-on` (or a requested analysis-warning gate), and `2` for invalid configuration or an unrecoverable scan error. HTML requires `--output`. GitHub workflow commands and SARIF 2.1.0 are supported.

Example terminal output:

```text
ArchAgent scan
Coverage: 1/1 files analyzed
Findings: 10 | Warnings: 0 | Redactions: 3
[CRITICAL] AA001 agent.py:21 - Unbounded agent loop
[CRITICAL] AA003 agent.py:11 - Ungated destructive action
```

## Privacy model

- Static scanning is the default and makes no network calls.
- `--judgment` is rejected unless `--send-code` is also present.
- Judgment sends only normalized evidence and bounded, redacted excerpts, grouped once per candidate rule. Requests use `gpt-5.6`, Pydantic Structured Outputs, `store=false`, a 2,000-token output ceiling, a 30-second timeout, and a six-rule call budget.
- Recognized OpenAI keys, AWS access keys, bearer tokens, email addresses, and US Social Security numbers are replaced before report or judgment output. Detection is intentionally narrow and is not a substitute for a dedicated secret/PII scanner.
- Nested `.gitignore` files, default build/dependency/generated exclusions, `.archagent-audit.yml`, 1 MiB per-file and 4 MiB aggregate limits, binary/non-Python exclusion, and explicit suppressions are honored. Production ArchAgent source is gated at zero suppressions.
- Refusal, timeout, authentication failure, or API failure never deletes static results; the report records `partial` or `failed` judgment status and an analysis warning.

No live API call is part of the offline test or acceptance suite. The submission smoke test requires a key and separate approval for paid usage.

## Rules

| ID | Architecture defect | Tier | Severity | Primary guidance |
|---|---|---|---|---|
| AA001 | Unbounded agent loop | Static | critical | [Agents SDK runner](https://openai.github.io/openai-agents-python/ref/run/) |
| AA002 | Missing output/run budget controls | Static | critical | [OpenAI practical guide](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf) |
| AA003 | Ungated destructive action | Static + judgment | critical | [Agents SDK approvals](https://openai.github.io/openai-agents-python/human_in_the_loop/), [OpenAI safety](https://developers.openai.com/api/docs/guides/agent-builder-safety) |
| AA004 | Unvalidated tool arguments | Static | critical | [OpenAI function calling](https://developers.openai.com/api/docs/guides/function-calling), [Anthropic tool definitions](https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools) |
| AA005 | Raw untrusted content in prompts | Judgment | critical | [OpenAI safety](https://developers.openai.com/api/docs/guides/agent-builder-safety), [Anthropic guardrails](https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/mitigate-jailbreaks) |
| AA006 | Secret or narrow PII exposure | Static | critical | [OpenAI safety](https://developers.openai.com/api/docs/guides/agent-builder-safety) |
| AA007 | Missing timeout or safe retry control | Static | warning | [OpenAI practical guide](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf) |
| AA008 | Unjustified orchestration complexity | Judgment | warning | [Anthropic effective agents](https://www.anthropic.com/engineering/building-effective-agents), [OpenAI practical guide](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf) |
| AA009 | Poor tool schema | Judgment | warning | [OpenAI function calling](https://developers.openai.com/api/docs/guides/function-calling), [Anthropic tool definitions](https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools) |
| AA010 | Unvalidated model output before side effect | Static + judgment | warning | [OpenAI function calling](https://developers.openai.com/api/docs/guides/function-calling), [OpenAI safety](https://developers.openai.com/api/docs/guides/agent-builder-safety) |
| AA011 | No agent eval coverage | Static + judgment | warning | [OpenAI evals](https://developers.openai.com/api/docs/guides/evals), [Google ADK evaluation](https://adk.dev/evaluate/) |
| AA012 | No agent observability | Static | info | [Agents SDK tracing](https://openai.github.io/openai-agents-python/tracing/) |

Each static verdict requires recognized syntax and source-backed evidence. Unsupported or dynamic constructs produce coverage gaps or analysis warnings; they are never silently declared clean.

## Supported and unsupported constructs

Recognized evidence includes:

- OpenAI `Runner.run`/`run_sync` limits: omitted `max_turns` is clean because the SDK default is bounded; explicit numeric limits are clean; `max_turns=None` is flagged.
- LangGraph `recursion_limit` when statically resolvable.
- `while True` loops with detectable exits, constant bounds, and simple recursive base cases.
- OpenAI Responses model calls, output caps, client/call timeouts, bounded client retries, and simple source-level run budgets.
- `@function_tool` approvals, its model-controlled parameters reaching common SQL/shell/file/network sinks, parameter-linked validation, agent eval markers/tests, and nearby logging/tracing evidence.

Known limitations:

- Python only. TypeScript and GitHub Actions output are not shipped.
- Dynamic imports, metaprogramming, dispatch beyond the supported one-hop project call graph, and runtime-only behavior remain inconclusive and produce coverage warnings when recognized.
- Static side-effect and schema analysis is conservative and can produce false positives; findings should be reviewed before planning.
- Secret/PII recognition covers a small explicit pattern set, not arbitrary credentials or personal data.
- No instruction-file linting, runtime tracing service, source-changing auto-fix, browser repository upload, account system, or package publication.

## Configuration

Create `.archagent-audit.yml` at the scan root:

```yaml
exclude:
  - generated/
  - vendor/
max_file_size: 1048576
```

Paths in reports are normalized relative to the scan root. Coverage records discovered, analyzed, and skipped files; detected frameworks; evaluated rules; rules not applicable; suppressions; analysis warnings; judgment status; and redaction counts.

## MCP registration

Run the stdio server directly with `archagent-audit serve`, or register the module with an MCP client:

```json
{
  "mcpServers": {
    "archagent": {
      "command": "python",
      "args": ["-m", "archagent_audit.mcp_server"],
      "cwd": "/absolute/path/to/this/repository"
    }
  }
}
```

Local mode exposes repository/file/source/diff audits, strict schema and loop checks, the rule catalog, review, and FIXPLAN generation. It is bounded to the configured canonical workspace root, including symlink defense, and may load only explicitly trusted local rulepacks.

Hosted Streamable HTTP mode registers only submitted-content tools. It has no repository or filesystem-path tools, never persists submitted code or results, and requires a private-beta bearer key configured as a SHA-256 digest in `ARCHAGENT_API_KEY_HASHES`. Both modes use the same `AuditService` pipeline and enforce `judgment=true, send_code=true` consent.

The functional landing and connection generator live in `web/`. `/connect` generates local stdio or hosted Codex MCP configuration; bearer keys remain in the user's local environment and are never entered into or transmitted by the page.

## Project evidence

- [Implementation specification](SPEC.md)
- [Goal prompt](GOAL.md)
- [Progress and self-scan triage](PROGRESS.md)
- [Validation report](tasks/validation-report.md)
- [Architecture compliance matrix](docs/architecture-compliance.md)
- [Reference production specification](specs/002-reference-production.md)
- [Hosted operations and rollback](docs/operations.md)
- [Under-three-minute demo script](docs/demo-script.md)

No repository, package, video, deployment, or submission is published by this project workflow without explicit approval.
