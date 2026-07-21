# Feature Spec: Release QA Hardening

## Purpose

Close the final 1.11.0 QA gaps without changing release identity or touching the live
service: make MCP rule applicability explicit, bind compliance to installed distribution
metadata, reject unknown scan selectors, and replace recovery dependency trees with one
clean web install.

## Scope

### In Scope

- Python MCP applicability and Report 2.2 coverage accounting for AA014-AA018.
- Installed `uptocode` metadata agreement with the 1.11.0 source contract.
- `scan --select` and `scan --ignore` validation for unknown rule identifiers.
- Removal of the one malformed root cache and six ignored web recovery directories.
- A clean lockfile-based web install and fresh local release-gate evidence.

### Out Of Scope

- New rules, changed rule findings, Report schema changes, or changed experimental output.
- Deployment, live `/healthz` repair, tags, releases, publication, or Marketplace actions.
- Operator-owned submission copy or assets already modified in the working tree.

## Functional Requirements

- Recognized Python MCP evidence independently makes AA014-AA018 applicable. AA014-AA016
  are stable evaluated rules; AA017-AA018 are experimental evaluated rules; none may be
  reported as not applicable for that language.
- Global coverage must aggregate actual per-language applicability, not depend solely on
  agent presence.
- Compliance fails when installed package metadata is absent or differs from `__version__`,
  `pyproject.toml`, or `server.json`.
- Core rule selectors are case-normalized. Unknown `--select` or `--ignore` identifiers
  fail before filtering or output with exit code 2 and an option-specific message. Custom
  identifiers exposed by the current report remain selectable.
- Cleanup deletes only the exact operator-authorized ignored paths. The external target of
  the existing `web/node_modules` junction must not be deleted.

## Acceptance Criteria

- [x] The standalone bad FastMCP fixture produces AA014-AA018 where its evidence applies,
  with matching global and Python coverage both with and without experimental inclusion.
- [x] Installed metadata and all source/manifest versions report 1.11.0; a simulated
  mismatch fails compliance.
- [x] Unknown select and ignore values exit 2; valid, normalized, duplicate, and custom
  selectors preserve filtering behavior.
- [x] The malformed root cache and six recovery trees are absent, `web/node_modules` is a
  local directory, and the dependency tree is valid after `npm ci`.
- [x] Pytest, Ruff, strict mypy, branch coverage at least 85%, acceptance, compliance, and
  web lint/type/build/tests all pass.
- [x] Fresh evidence is recorded without deployment or publication.

## Risks / Safety Checks

- Resolve and verify every deletion target remains inside the repository before removal.
- Remove the current web junction itself without recursively deleting its external target.
- Preserve the strict Report 2.2 shape and existing visibility of experimental findings.
- Preserve all unrelated operator-owned working-tree changes.
