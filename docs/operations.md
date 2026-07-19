# Hosted MCP Operations

The hosted service is private-beta, stateless, and submitted-content-only. Deployment is an explicit operator action and must use the reviewed image digest and `deploy/cloud-run-service.yaml` limits.

## Pre-deploy gate

1. Confirm CI, compliance, SBOM, container, and hosted MCP lifecycle artifacts are green.
2. Confirm `ARCHAGENT_API_KEY_HASHES` and `OPENAI_API_KEY` resolve from Secret Manager; never print or export their values.
3. Confirm Cloud Run is limited to 1 CPU, 1 GiB, concurrency 4, maximum 3 instances, and a 300-second platform timeout. The application deadline remains shorter.
4. Obtain explicit publication/deployment approval.

## Payload-free monitoring

Monitor request counts, HTTP status classes, duration, concurrency, instance count, memory, rule-result counts, judgment request/token totals, and sanitized error classes. Logs and labels must not contain source, excerpts, prompts, authorization headers, keys, email addresses, SSNs, filenames supplied by hosted users, or report bodies.

Configure budget alerts for Cloud Run, Artifact Registry, Secret Manager, and authorized OpenAI usage before traffic is enabled. Treat alert changes as operator-approved infrastructure changes.

## Synthetic health check

- `GET /healthz` and `GET /readyz` must return status and version without authentication or payload data.
- An authenticated `check_loop` call using only synthetic `while True` code must return AA001.
- A request without a bearer token must return 401.
- Hosted tool discovery must not contain `audit_file` or `audit_repo`.
- Model judgment smoke is separate, paid, synthetic, and requires explicit authorization.

## Rollback

1. Route all traffic back to the last known-good Cloud Run revision by immutable revision name.
2. Disable the failed revision; do not debug using customer payloads.
3. Rotate private-beta keys if authorization or log handling is implicated.
4. Preserve only payload-free platform logs, image digest, compliance artifact, SBOM, metrics, and sanitized error class for incident review.
5. Re-run the hosted lifecycle, no-persistence, log-capture, and compliance gates before promoting a corrected revision.

