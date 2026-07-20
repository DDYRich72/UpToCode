# UpToCode site

The competition site contains exactly two product routes: the landing page at `/`
and the MCP setup guide at `/connect`. It runs on
[vinext](https://github.com/cloudflare/vinext) and has no database, account, or
credential-collection surface.

## Prerequisites

- Node.js `>=22.13.0`

## Local verification

```bash
npm ci
npm run dev
npm run lint
npx tsc --noEmit
npm test
```

`npm test` performs a production build, server-renders both routes, and checks
that the connection guide does not collect an API key or advertise a nonexistent
hosted endpoint. The tracked Sites plugin copies only the empty hosting manifest;
there are no D1, R2, or migration bindings.

## Commands

- `npm run dev`: start local development
- `npm run build`: verify the production vinext output
- `npm test`: build and verify both rendered routes and site contracts
- `npm run lint`: run ESLint
- `npx tsc --noEmit`: run the TypeScript compiler as a site build check; TypeScript
  analysis in the UpToCode scanner remains deferred to 1.1

## Learn More

- [vinext Documentation](https://github.com/cloudflare/vinext)
