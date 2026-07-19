# Submission Evidence

These files are sanitized, reproducible captures from the offline ArchAgent workflow.
They contain checked-in synthetic fixtures only—no credentials, private external source,
account identifiers, Codex Session ID, or live model payloads.

| Artifact | What it proves |
|---|---|
| `bad-fixture-terminal.txt` | Critical-threshold scan, coverage, findings, warnings, and redactions |
| `bad-fixture-report.html` | Standalone human-readable report with coverage and finding evidence |
| `aa006-redacted.json` | Recognized synthetic secret is replaced before report output |
| `review-manifest.json` | Human decisions bound to the exact report fingerprint |
| `FIXPLAN.md` | Approved-only, non-mutating Codex implementation hand-off |
| `mcp-check-loop.json` | Real stdio MCP discovery and AA001 `check_loop` response |
| `acceptance.txt` | Offline acceptance runner result and ten-tool stdio probe |
| `validation-matrix.md` | Phase gate environments, commands, counts, and coverage |

`bad-fixture-report.json` is retained as the machine-readable source used by the review
and plan commands. The synthetic AA006 example is explicitly labeled and redacted.
