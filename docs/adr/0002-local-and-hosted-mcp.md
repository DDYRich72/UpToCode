# ADR 0002: Local and Hosted MCP Modes

Local stdio mode resolves one canonical configured workspace root when the server is
created; every relative or absolute file, repository, and diff-base path is contained
against it. Hosted
Streamable HTTP mode registers only submitted-content tools, loads no external
rulepacks, and persists no code. The two modes share typed use cases, not access
capabilities.

FastMCP owns protocol parsing, structured outputs, annotations, resources,
progress, cancellation propagation, and Streamable HTTP. ArchAgent augments the
SDK-generated argument models to reject unknown fields and publish
`additionalProperties: false`, because MCP SDK 1.28.1 does not expose that setting
on `add_tool`. The package is pinned to 1.28.1. Every private attribute is guarded,
server creation fails closed with the installed SDK version when the contract changes,
and the strict-schema upgrade canary is required before changing the pin.
