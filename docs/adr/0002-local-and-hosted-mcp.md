# ADR 0002: Local and Hosted MCP Modes

Local stdio mode may inspect only a canonical configured workspace root. Hosted
Streamable HTTP mode registers only submitted-content tools, loads no external
rulepacks, and persists no code. The two modes share typed use cases, not access
capabilities.

FastMCP owns protocol parsing, structured outputs, annotations, resources,
progress, cancellation propagation, and Streamable HTTP. ArchAgent augments the
SDK-generated argument models to reject unknown fields and publish
`additionalProperties: false`, because MCP SDK 1.28 does not expose that setting
on `add_tool`. The package is therefore capped to the tested 1.28 minor and the
strict-schema regression suite is required before any SDK range update.
