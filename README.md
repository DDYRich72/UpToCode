# UpToCode

<!-- mcp-name: io.github.DDYRich72/uptocode -->

[![PyPI version](https://img.shields.io/pypi/v/uptocode.svg)](https://pypi.org/project/uptocode/)
[![Scanned with UpToCode](https://img.shields.io/badge/scanned%20with-UpToCode-175cd3)](https://github.com/DDYRich72/UpToCode)

UpToCode is a design-time architecture-quality scanner for Python agent applications. It finds missing execution bounds, run budgets, approvals, validation, resilience controls, evals, and observability; explains the evidence; and produces an approval-driven plan for Codex without rewriting source code.

The product is deliberately narrower than a general agent-security scanner. Version 1.1 recognizes OpenAI Agents SDK patterns, LangGraph limits, conservative custom Python agent loops, and positive evidence of unbounded context growth. Static scans are local and offline. Optional GPT‑5.6 judgment is explicit, bounded, redacted, and code-sharing gated.

> The Python distribution, import package, and command are all `uptocode`. Version 1.0.0
> is the published PyPI release; this source tree is prepared as 1.1.0 for the operator-gated release.

## Install locally

UpToCode requires Python 3.11 or newer. Install the verified 1.0 release from PyPI:

```text
python -m pip install "uptocode==1.0.0"
uptocode --help
```

For repository development, use the editable test environment:

```text
python -m pip install -e ".[test]"
uptocode --help
```

All ordinary tests are mocked/offline:

```text
python -m pytest -q
python scripts/acceptance.py
```

## Judge test build

The repository and package are public. No hosted credential or paid model call is required
for the complete offline test build.

```text
git clone https://github.com/DDYRich72/UpToCode.git
cd UpToCode
python -m venv .venv
```

Activate the environment with `.venv\Scripts\activate` on Windows PowerShell or
`source .venv/bin/activate` on POSIX, then run:

```text
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
uptocode scan fixtures/bad_python --fail-on critical
uptocode scan fixtures/bad_python --format json --output report.json
uptocode review report.json --approve AA001,AA003 --reject AA012 --non-interactive
uptocode plan report.json --manifest .uptocode/manifest.json --output FIXPLAN.md
python scripts/acceptance.py
```

The first scan intentionally exits `1` because the fixture contains critical findings.
The remaining commands produce a report-bound review manifest and an approved-only
`FIXPLAN.md`; they do not edit the fixture. To inspect the local MCP surface, run
`uptocode serve --transport stdio --root .` from an MCP client or use the JSON
registration under [MCP registration](#mcp-registration). `python scripts/acceptance.py`
also launches a real stdio server, lists all ten tools, and calls `check_loop` offline.

The submitted-content hosted transport is deployed at
`https://uptocode-mcp-1015314816960.us-central1.run.app/mcp`. Its bearer credential is
issued separately and read from `UPTOCODE_API_KEY`; never commit it or enter it into the
website. The immutable production revision passed readiness, unauthorized-access, AA001,
tool-discovery, judgment-gate, rate-limit, and payload-free-log checks. Hosted judgment is
off, no OpenAI key is attached, and verification made zero paid model calls.

## Scan, review, plan

```text
uptocode scan PATH [--format terminal|json|html|github|sarif] [--output FILE]
                         [--judgment --send-code]
                         [--fail-on critical|warning|info]
                         [--include-experimental] [--share-safe]
                         [--baseline FILE|--update-baseline FILE]
                         [--changed-since REF] [--select RULES] [--ignore RULES]
                         [--exclude GLOB] [--severity RULE=LEVEL]
                         [--fail-on-analysis-warning] [--github-summary PATH]
                         [--verbose]
uptocode review REPORT [--approve IDS|--approve-all] [--reject IDS]
                              [--reuse MANIFEST] [--non-interactive]
uptocode plan REPORT --manifest MANIFEST [--output FIXPLAN.md]
uptocode serve --transport stdio --root PATH
uptocode serve --transport streamable-http --mode hosted
```

The v1 workflow is non-mutating:

```text
uptocode scan . --format json --output report.json
uptocode review report.json --approve AA001,AA003 --reject AA012 --non-interactive
uptocode plan report.json --manifest .uptocode/manifest.json --output FIXPLAN.md
```

`review` binds decisions to the exact report fingerprint. `plan` refuses a mismatched manifest and includes only approved findings. Neither command edits the scanned repository.

Exit codes are `0` for no configured threshold breach, `1` for a finding at or above `--fail-on` (or a requested analysis-warning gate), and `2` for invalid configuration or an unrecoverable scan error. Experimental findings remain visible but require `--include-experimental` to affect `--fail-on`. `--share-safe` sanitizes JSON, HTML, or SARIF for distribution while retaining the repository revision. Baseline 2.1 reports new, aging, and resolved debt and preserves `first_seen` when updated. Suppressions may include `owner`, quoted `reason`, and an inclusive `expires` date. HTML requires `--output`. GitHub workflow commands escape untrusted command data and properties. SARIF 2.1.0 omits absent fields, declares default rule levels, and carries stable partial fingerprints. `--github-summary PATH` appends a bounded Markdown summary; when `GITHUB_STEP_SUMMARY` is set, the summary is appended there automatically.

## Pre-commit

```yaml
repos:
  - repo: https://github.com/DDYRich72/UpToCode
    rev: v1.1.0
    hooks:
      - id: uptocode
```

Run `pre-commit install`, then use `pre-commit run uptocode --all-files`. To copy the
project badge into your own README:

```markdown
[![Scanned with UpToCode](https://img.shields.io/badge/scanned%20with-UpToCode-175cd3)](https://github.com/DDYRich72/UpToCode)
```

## GitHub Action

The repository ships a composite Action that installs UpToCode from the Action checkout,
runs the scan, uploads SARIF with `always()`, and only then returns the preserved scanner
exit code:

```yaml
permissions:
  contents: read
  security-events: write

steps:
  - uses: actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0 # v7
  - uses: DDYRich72/UpToCode@v1.0.0
    with:
      path: .
      fail-on: critical
      version: source
      upload-sarif: "true"
```

`version: source` installs from the checked-out Action source. An exact semantic version,
such as `1.0.0`, installs the matching `uptocode` PyPI release. Set
`upload-sarif: "false"` when code-scanning
upload is not desired; otherwise the calling workflow needs `security-events: write`.

Example terminal output:

```text
UpToCode scan
Coverage: 1/1 files analyzed
Findings: 11 | Warnings: 0 | Redactions: 3
[CRITICAL] AA001 agent.py:21 - Unbounded agent loop
[CRITICAL] AA003 agent.py:11 - Ungated destructive action
```

## Privacy model

- Static scanning is the default and makes no network calls.
- `--judgment` is rejected unless `--send-code` is also present.
- Judgment sends only normalized evidence and bounded, redacted excerpts, grouped once per candidate rule. Requests use `gpt-5.6`, Pydantic Structured Outputs, `store=false`, a 2,000-token output ceiling, a 30-second timeout, and a six-rule call budget.
- Recognized OpenAI keys, AWS access keys, bearer tokens, email addresses, and US Social Security numbers are replaced before report or judgment output. Detection is intentionally narrow and is not a substitute for a dedicated secret/PII scanner.
- Nested `.gitignore` files, default build/dependency/generated exclusions, `.uptocode.yml`, 1 MiB per-file and 4 MiB aggregate limits, binary/non-Python exclusion, and explicit suppressions are honored. Production UpToCode source is gated at zero suppressions.
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
| AA007 | Missing timeout, retry, or retry backoff | Static | warning | [OpenAI practical guide](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf) |
| AA008 | Unjustified orchestration complexity | Judgment | warning | [Anthropic effective agents](https://www.anthropic.com/engineering/building-effective-agents), [OpenAI practical guide](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf) |
| AA009 | Poor tool schema | Judgment | warning | [OpenAI function calling](https://developers.openai.com/api/docs/guides/function-calling), [Anthropic tool definitions](https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools) |
| AA010 | Unvalidated model output before side effect | Static + judgment | warning | [OpenAI function calling](https://developers.openai.com/api/docs/guides/function-calling), [OpenAI safety](https://developers.openai.com/api/docs/guides/agent-builder-safety) |
| AA011 | No agent eval coverage | Static + judgment | warning | [OpenAI evals](https://developers.openai.com/api/docs/guides/evals), [Google ADK evaluation](https://adk.dev/evaluate/) |
| AA012 | No agent observability | Static | info | [Agents SDK tracing](https://openai.github.io/openai-agents-python/tracing/) |
| AA013 | Unbounded context growth | Static | warning | [Anthropic effective agents](https://www.anthropic.com/engineering/building-effective-agents), [OpenAI practical guide](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf) |

Each static verdict requires recognized syntax and source-backed evidence. Unsupported or dynamic constructs produce coverage gaps or analysis warnings; they are never silently declared clean.

## Supported and unsupported constructs

Recognized evidence includes:

- OpenAI `Runner.run`/`run_sync` limits: omitted `max_turns` is clean because the SDK default is bounded; explicit numeric limits are clean; `max_turns=None` is flagged.
- LangGraph `recursion_limit` when statically resolvable.
- `while True` loops with detectable exits, constant bounds, and simple recursive base cases.
- OpenAI Responses model calls, output caps, client/call timeouts, bounded client retries, and simple source-level run budgets.
- `@function_tool` approvals, its model-controlled parameters reaching common SQL/shell/file/network sinks, parameter-linked validation, agent eval markers/tests, and nearby logging/tracing evidence.

Known limitations:

- Python analysis only; TypeScript analysis remains deferred to 1.1. GitHub workflow
  annotations, Markdown summaries, SARIF, and the reusable composite Action are delivery
  surfaces for the Python scanner, not TypeScript analyzers.
- Dynamic imports, metaprogramming, dispatch beyond the supported one-hop project call graph, and runtime-only behavior remain inconclusive and produce coverage warnings when recognized.
- Static side-effect and schema analysis is conservative and can produce false positives; findings should be reviewed before planning.
- Secret/PII recognition covers a small explicit pattern set, not arbitrary credentials or personal data.
- No instruction-file linting, runtime tracing service, source-changing auto-fix, browser repository upload, or account system.

## Configuration

Create `.uptocode.yml` at the scan root:

```yaml
exclude:
  - generated/
  - vendor/
max_file_size: 1048576
```

Paths in reports are normalized relative to the scan root. Coverage records discovered, analyzed, and skipped files; detected frameworks; evaluated rules; rules not applicable; suppressions; analysis warnings; judgment status; and redaction counts.

## MCP registration

Run the stdio server directly with `uptocode serve`, or register the module with an MCP client:

```json
{
  "mcpServers": {
    "uptocode": {
      "command": "python",
      "args": ["-m", "uptocode.mcp_server"],
      "cwd": "/absolute/path/to/this/repository"
    }
  }
}
```

Local mode exposes repository/file/source/diff audits, strict schema and loop checks, the rule catalog, review, and FIXPLAN generation. It is bounded to the configured canonical workspace root, including symlink defense, and may load only explicitly trusted local rulepacks.

Hosted Streamable HTTP mode registers only submitted-content tools. It has no repository or
filesystem-path tools, never persists submitted code or results, and requires private-beta
bearer keys configured as SHA-256 digests in `UPTOCODE_API_KEY_HASHES`. Authenticated
requests use an in-memory per-key token bucket (`UPTOCODE_RATE_LIMIT_PER_MINUTE`, default
`30`); excess requests return `429` with `Retry-After`. Logs attribute traffic only to an
eight-character digest prefix. Hosted judgment is rejected unless
`UPTOCODE_HOSTED_JUDGMENT=true`; the default is `false`. The double-consent
`judgment=true, send_code=true` rule still applies when the global gate is enabled.

Local mode resolves its canonical workspace root once when the server is created. Relative
and absolute file, repository, and diff-base paths are all contained against that same root,
including symlink resolution. The pinned MCP SDK compatibility guard fails server startup
with the installed SDK version if the strict-schema private contract changes; the upgrade
procedure is documented in `docs/operations.md`.

The functional landing and connection generator live in `web/`. `/connect` generates local stdio or hosted Codex MCP configuration; bearer keys remain in the user's local environment and are never entered into or transmitted by the page.

## UpToCode audits itself

The release gate runs `python scripts/compliance.py` against UpToCode's production Python
source. The current verified result is zero findings, zero suppressions, and zero unexplained
analysis warnings. Deliberately bad fixtures and synthetic redaction sentinels remain test
evidence and are excluded from that production claim. This dogfood check is part of every
release candidate, alongside the full offline suite and branch-coverage floor.

## Built with Codex and GPT-5.6

Codex was the development collaborator throughout UpToCode: it translated the product
specification into vertical slices, implemented and reviewed the scanner, CLI, reports,
MCP servers, site, and tests, fixed clean-clone defects, and ran the Windows/POSIX
submission gates. UpToCode also produces a report-bound `FIXPLAN.md` with a copy-paste
Codex hand-off, so approval—not automatic source mutation—connects analysis to coding.
The competition-first work order, decisions, progress log, and validation report remain
in the repository as an auditable record of that collaboration.

GPT-5.6 powers the optional judgment tier through OpenAI Responses Structured Outputs.
It evaluates only bounded, redacted evidence for candidate rules that need contextual
judgment. The feature is opt-in twice (`--judgment --send-code`), uses `store=false`, and
never replaces or deletes deterministic static findings when a request fails or is
refused. Ordinary tests, the judge test build, and the demo dry-run are entirely offline;
any live paid call requires separate operator approval.

## Project evidence

- [Implementation specification](SPEC.md)
- [Goal prompt](GOAL.md)
- [Progress and self-scan triage](PROGRESS.md)
- [Validation report](tasks/validation-report.md)
- [Architecture compliance matrix](docs/architecture-compliance.md)
- [Reference production specification](specs/002-reference-production.md)
- [Hosted operations and rollback](docs/operations.md)
- [Hosted judge access](docs/hosted-judge-access.md)
- [Under-three-minute demo script](docs/demo-script.md)
- [Event rules and evidence checklist](docs/event-rules.md)
- [Submission evidence index](docs/submission-evidence/README.md)

No repository, package, video, deployment, or submission is published by this project workflow without explicit approval.
