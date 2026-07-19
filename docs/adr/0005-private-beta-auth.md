# ADR 0005: Private-Beta Hosted Authorization

Hosted MCP uses revocable high-entropy bearer keys stored as hashes in managed
secrets. This is a controlled beta boundary, not a replacement for OAuth in a
self-service product. Each authorized credential digest receives a bounded in-memory
token bucket (30 requests/minute by default), and authenticated logs contain only an
eight-character digest prefix. Authorization headers, raw keys, full digests, and request
payloads are never logged. Hosted model judgment is globally disabled unless the operator
explicitly sets `ARCHAGENT_HOSTED_JUDGMENT=true`; per-request code-sharing consent remains
required after that gate.
