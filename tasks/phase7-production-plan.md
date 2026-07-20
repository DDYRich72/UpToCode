# Phase 7 Production Plan — UpToCode

Authority: `tasks/completion-plan-v2.md` Phase 7 and DECISIONS D005–D008.

## Stage 1 — Canonical identity

- Rename the package/import/CLI and every current product surface to UpToCode.
- Keep AA001–AA012 identifiers stable and preserve the frozen submission tag.
- Update tests, fixtures, generated evidence, deployment templates, and docs together.

## Stage 2 — Production release mechanics

- Recheck `uptocode` on PyPI immediately before publication.
- Add isolated build/install verification and tag-driven trusted publishing.
- Generate SBOM/provenance artifacts and enable attestations for the public release.
- Validate the final `server.json` against the official MCP Registry schema/tooling.

## Stage 3 — Hosted migration

- Prepare `uptocode-mcp` resources with `UPTOCODE_*` settings and no paid-model key.
- Stop for deployment approval.
- Deploy by immutable digest, verify the full hosted control surface, and update the
  manifest/site/docs to the exact new endpoint.

## Stage 4 — Publication checkpoints

- Stop for approval before changing repository visibility.
- Stop for approval before configuring/publishing to PyPI.
- Stop for approval before MCP Registry submission.
- Stop for approval before any paid GPT-5.6 smoke call.

## Stage 5 — 1.1 specifications

- Write a separate Firestore beta-access specification that remains unimplemented.
- Write a separate TypeScript analysis specification with a real parser and explicit
  per-language rule applicability; do not implement it in this production train.

## Exit gate

Run the full Windows/POSIX gate, wheel-environment audit, site checks, container checks,
claim synchronization, clean-tree verification, and production-release dry-runs. Record
exact evidence in `tasks/validation-report.md` and `PROGRESS.md`.
