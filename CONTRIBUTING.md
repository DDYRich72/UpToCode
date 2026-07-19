# Contributing

1. Read `docs/constitution.md`, `docs/architecture.md`, and the relevant feature spec.
2. Add or identify the failing invariant before implementation.
3. Keep deterministic rules pure and route interfaces through `AuditService`.
4. Do not add production suppressions, hidden network calls, or permissive public contracts.
5. Run `python scripts/acceptance.py`, the production compliance script, and the site build when applicable.
6. Update `tasks/validation-report.md` with acceptance evidence.

External rulepacks execute trusted local code. Never enable them in hosted mode.
