# Security Policy

## Supported version

Security fixes target the current 1.x release line.

## Reporting

Do not open a public issue containing credentials, private source, or exploit details.
Use the repository host's private security-reporting channel after publication.

## Boundaries

- Static scans are offline.
- Hosted mode accepts submitted content only and persists no code.
- Judgment requires explicit code-sharing consent and receives bounded redacted excerpts.
- Local path tools enforce a canonical configured workspace root.
- External Python rulepacks are trusted-code extensions and are disabled in hosted mode.

Generated reports are security-sensitive artifacts and should be handled according to the
sensitivity of their source repositories.
