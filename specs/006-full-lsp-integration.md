# Feature Spec: Full LSP Integration

Status: approved for Batch 4.1 implementation on 2026-07-21.

## Purpose

Replace the thin save-time VS Code subprocess integration with a persistent language
server that gives developers fast, CLI-equivalent, file-scoped diagnostics and explicit
navigation and suppression actions without adding background repository analysis.

## User story

As an agent application developer, I want UpToCode findings and their evidence available
in my editor after each save so that I can investigate or suppress a finding without
waiting for a new CLI process or leaving the current document.

## Scope

### In scope

- A `pygls` 2.x stdio language server launched by the public `uptocode lsp` command.
- Incremental LSP document synchronization for Python and the supported TypeScript
  language modes (`.py`, `.ts`, `.tsx`, and `.mts`).
- File-scoped static analysis on document open and save through the existing
  `AuditService`; no rule logic may be reimplemented in the server.
- Diagnostics with parity to the default static CLI scan for rule id, fingerprint,
  severity, line, maturity, message, and primary citation.
- Code actions to suppress a finding with structured metadata, open its primary public
  citation, and open its exact-fingerprint entry in a workspace-root `FIXPLAN.md`.
- A persistent VS Code language client and deterministic offline integration tests.

### Out of scope

- Whole-repository indexing, background workspace scans, or analysis on every keystroke.
- Judgment calls, hosted services, network requests, trace ingestion, or local-model work.
- Automatic fixes, automatic saves, repository-wide edits, Git operations, runner
  execution, commits, merges, or Marketplace/PyPI publication.
- New rules, changed rule semantics, or changes to Report 2.2 and ReviewManifest 2.0.
- JavaScript or any source extension not already supported by the CLI.

## Public contracts

- `uptocode lsp` runs an LSP server over stdin/stdout. Protocol messages are the only
  stdout content; diagnostics, logs, and failures never corrupt the protocol stream.
- The server advertises incremental text synchronization and code actions. It analyzes
  only the affected supported file on open/save and clears its diagnostics on close.
- A successful LSP scan emits the same findings as `AuditService.scan(file)` under the
  same local configuration. Analysis warnings are logged through LSP and are not
  presented as rule findings.
- Each diagnostic carries the finding fingerprint and citation data required by code
  actions. Diagnostic ranges remain full-line because Report 2.2 has no column contract.
- The VS Code extension retains `uptocode.executable` and removes the subprocess-only
  `uptocode.extraArgs` and `uptocode.failOn` settings. `.uptocode.yml` is the scanning
  policy source of truth.
- UpToCode is versioned as 1.11.0 and the VS Code extension as 0.2.0 for this lane.

## Functional requirements

- A persistent server process must keep protocol handling responsive by performing scans
  outside the LSP event loop. A newer document version supersedes an older pending scan,
  whose results must never replace current diagnostics.
- Open and save trigger analysis; incremental changes update the server's document state
  but do not trigger analysis before save. Unsupported languages and non-file URIs are
  ignored without clearing unrelated diagnostics.
- Clean scans publish an empty diagnostic set. Scan, parse, or configuration failures
  clear stale diagnostics for that document and produce a bounded, source-free log
  message.
- Immutable rule metadata and workspace configuration may be cached within the server.
  Configuration and configured local rulepacks must be reloaded after their source file
  changes; caches must never broaden discovery into a repository scan.
- The suppression action must prompt for owner, reason, and expiry, default expiry to 30
  days from the local date, and reject invalid owner characters, quotes/newlines in the
  reason, malformed dates, and past dates. Cancellation makes no edit.
- The suppression edit must use `#` for Python and `//` for TypeScript, preserve the
  document's indentation and line ending, target the current document version, and emit
  exactly `uptocode: ignore AAxxx owner=... reason="..." expires=YYYY-MM-DD` at a safe
  statement boundary. It must not save the file automatically.
- The citation action opens only the diagnostic's first registry-resolved URL. The
  FIXPLAN action resolves an exact fingerprint in workspace-root `FIXPLAN.md`; it is
  disabled with a reason when the workspace, file, or entry is absent.

## Performance contract

- The checked-in representative performance fixture is a 300–500-line supported agent
  module and is analyzed through the in-process LSP path.
- After one warm-up scan, 20 consecutive save-to-published-diagnostics measurements must
  have p95 latency below 200 ms on the recorded Windows and POSIX release environments.
- CI verifies that only the changed file is analyzed and that stale results are rejected;
  the 200 ms wall-clock measurement is recorded at the release gate rather than enforced
  as a flaky shared-runner test.

## Risks and safety checks

- This feature narrowly changes D012's no-source-edit contract. No implementation may
  begin until the operator acknowledges this spec and proposed D013.
- The language server and its tests remain offline. Opening a citation occurs only after
  a user invokes the action; the server itself does not fetch the URL.
- The explicit suppression edit is the only new mutation surface. It is limited to one
  version-checked edit in the active document and never auto-saves.
- LSP stdout contamination, stale-result races, invalid edit placement, multi-root path
  confusion, and raw source in logs are release-blocking defects.

## Acceptance criteria

- [x] The operator acknowledged this spec and D013 on 2026-07-21 before RED tests or
  implementation.
- [x] `uptocode lsp` completes initialize, open, incremental change, save, close,
  shutdown, and exit flows through an in-process pygls client harness.
- [x] Python and supported TypeScript diagnostics match default static CLI findings for
  every rule capable of producing one; judgment-only rules remain `not_requested`.
- [x] Rapid saves cannot publish an older document version over a newer one, and clean,
  closed, malformed, failed, unsupported, and non-file cases have deterministic behavior.
- [x] Suppression succeeds end to end for Python and TypeScript, the next scan removes the
  finding, and the CLI records its structured metadata; invalid or cancelled prompts do
  not edit the document.
- [x] Citation and exact-fingerprint FIXPLAN actions work, including disabled missing and
  stale-entry states, multi-root workspaces, and paths containing spaces.
- [x] Twenty warm representative save cycles record p95 below 200 ms on Windows and
  POSIX, with no whole-repository analysis.
- [x] Python tests, acceptance, compliance, Ruff, strict mypy, branch coverage at least
  85%, site checks, extension typecheck/tests/build/VSIX, production dogfood, deliberate
  goldens, version agreement, and clean-tree checks pass.
- [x] Documentation, CHANGELOG, progress, and validation evidence match the shipped
  surface; release tags and publication remain operator-only.

## Implementation sequence after acknowledgment

1. Add failing server contract, parity, action, race, and latency-harness tests.
2. Add the pygls server and `uptocode lsp` entrypoint using the existing audit service.
3. Replace the extension subprocess adapter with the persistent language client and
   explicit client-side suppression/navigation commands.
4. Satisfy focused tests, then run and record the complete cross-platform exit gate.
5. Stop for operator review before creating or pushing `v1.11.0` or publishing anything.
