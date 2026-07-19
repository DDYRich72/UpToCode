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

## Accepted dependency risk

As of 2026-07-19, the site accepts one moderate production/build dependency advisory,
represented by the `next` and nested `postcss` records in `npm audit --omit=dev`:

- `GHSA-qx2v-qp2m-jg93` affects the PostCSS copy vendored by Next.js 16.2.10. The
  vulnerable behavior requires stringifying attacker-controlled CSS containing a closing
  `style` tag. ArchAgent serves only checked-in static CSS, has no CSS editor or upload
  surface, and does not pass request data to PostCSS. npm currently offers only an unsafe
  downgrade to Next.js 9.3.3, so the available automated fix is rejected.

Revisit this decision by 2026-08-02, or immediately when a compatible Next.js release
vendors PostCSS 8.5.10 or newer. High and critical npm advisories remain release blockers.
