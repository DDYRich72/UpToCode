# Feature Spec: Reference-Grade Production 1.0

## Purpose

Make UpToCode the reference implementation of AA001-AA012 across its CLI,
analyzer, judgment tier, MCP servers, hosted service, and release workflow.

## In scope

- Report 2.0, stable fingerprints, per-rule outcomes, baselines, SARIF, and manifest reuse.
- Robust discovery, configuration, diff reconstruction, schema validation, and bounded evidence flow.
- Local stdio MCP and stateless hosted Streamable HTTP MCP with strict typed tools.
- Trusted local rulepacks, judgment hardening, CI/release/container evidence, and a functional landing/connect site.

## Out of scope

- Browser repository uploads, Git cloning, TypeScript analysis, source-changing auto-fix, runtime tracing service, self-service accounts, and visual polish.

## Acceptance criteria

- [ ] Production source self-scan has zero findings, suppressions, and unexplained warnings.
- [ ] Every AA001-AA012 control has passing implementation and test evidence.
- [ ] All public inputs and outputs are strict typed contracts.
- [ ] Local MCP cannot escape its configured root; hosted MCP exposes no path tools and persists no code.
- [ ] Static scans make no network calls; judgment remains explicitly consent gated.
- [ ] Windows, Linux, and macOS validation covers supported Python versions.
- [ ] Installed wheel, local MCP, hosted container, and landing site builds pass.

## Safety

Publication, deployment, paid API calls, package-name selection, and judge-key
distribution remain explicit operator approval gates.
