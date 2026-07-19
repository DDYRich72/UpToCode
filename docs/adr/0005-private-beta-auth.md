# ADR 0005: Private-Beta Hosted Authorization

Hosted MCP uses revocable high-entropy bearer keys stored as hashes in managed
secrets. This is a controlled beta boundary, not a replacement for OAuth in a
self-service product. Authorization headers and request payloads are never logged.
