# Hosted Judge Access

This is the operator hand-off for the optional Phase 5 Cloud Run service. The repository
and PyPI package remain private/unpublished. The Cloud Run URL is network-reachable so a
standard MCP client can use one `Authorization` header, but every non-health request is
protected by ArchAgent's high-entropy bearer key. Cloud Run IAM is deliberately disabled
at this edge because it would otherwise consume that same header before the application.

The checked-in deployment template attaches only the SHA-256 allowlist secret. Hosted
judgment remains `false`, and no `OPENAI_API_KEY` is attached or needed. This phase performs
no paid model call.

## Judge connection

The endpoint is `https://archagent-mcp-1015314816960.us-central1.run.app/mcp`. The operator
places only the raw credential in the private Devpost testing notes—not in Git, screenshots,
logs, or the demo video. A judge sets
the credential locally and registers the hosted server in Codex:

```powershell
$env:ARCHAGENT_API_KEY = "<credential supplied in private submission notes>"
```

```toml
[mcp_servers.archagent]
url = "https://archagent-mcp-1015314816960.us-central1.run.app/mcp"
bearer_token_env_var = "ARCHAGENT_API_KEY"
required = true
startup_timeout_sec = 20
tool_timeout_sec = 240
```

Expected hosted discovery contains only submitted-content tools. It must not expose
`audit_file` or `audit_repo`. A quick judge exercise is:

1. Discover tools and call `check_loop` with `while True:\n    work()`; confirm AA001.
2. Call `audit_source` with a small pasted snippet; confirm a bounded Report 2.0 response.
3. Optionally call `check_tool_schema` with a deliberately loose schema and inspect the
   actionable strictness issues.

The credential is revocable and rate-limited per Cloud Run instance. A `429` includes
`Retry-After`; wait before retrying. Hosted judgment is intentionally unavailable for the
judge endpoint, so `judgment=true` returns a clear gate error and spends no model credits.

## Operator-only deployment sequence

The commands and evidence procedure are maintained in [Hosted MCP Operations](operations.md).
They require separate authorization for deployment and credential generation. Do not add a
real `server.json` remote, change the website's no-endpoint claim, or prepare private
submission notes until the live URL passes every synthetic check.

## Evidence boundary

The 2026-07-19 live smoke passed readiness, unauthorized access, hosted discovery, AA001,
the judgment gate, and rate limiting without a paid model call. The automated live smoke writes sanitized evidence under `.archagent-audit/`, which is
ignored by Git. It records the endpoint, version, safe eight-character key ID, tool names,
and pass/fail controls, but never the raw key or full digest. Exported Cloud Run logs must
then pass `scripts/verify_hosted_logs.py` before the credential is distributed.
