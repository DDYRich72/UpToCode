# Hosted MCP Operations

The hosted service is stateless and submitted-content-only. Deployment is an explicit
operator action and must use the reviewed image digest and `deploy/cloud-run-service.yaml`
limits. Cloud Run is network-reachable for standard MCP clients, while the application
bearer boundary protects every non-health route. This avoids a second Cloud Run IAM bearer
token consuming the `Authorization` header intended for UpToCode.

Production state: `uptocode-mcp` revision `uptocode-mcp-00001-szq` serves
`https://uptocode-mcp-1015314816960.us-central1.run.app/mcp`, pinned to image digest
`sha256:309f90c591b1072dacc16726366f4319fd4996c2b4cdb9230c37d14c94e12091`.
Hosted judgment is disabled and no OpenAI key is attached.

## Pre-deploy gate

1. Confirm CI, compliance, SBOM, container, and hosted MCP lifecycle artifacts are green.
2. Confirm `UPTOCODE_API_KEY_HASHES` resolves from Secret Manager; never print or export
   its values. The production manifest does not attach `OPENAI_API_KEY`; paid hosted judgment
   remains deferred and disabled.
3. Confirm Cloud Run is limited to 1 CPU, 1 GiB, concurrency 4, maximum 3 instances, and a 300-second platform timeout. The application deadline remains shorter.
4. Confirm `UPTOCODE_RATE_LIMIT_PER_MINUTE` is a positive integer (default `30`) and
   `UPTOCODE_HOSTED_JUDGMENT` is exactly `false` unless the operator explicitly approves
   hosted paid judgment.
5. Obtain explicit publication/deployment approval.

The repository contains no Google Cloud credentials or deployment automation identity.
The operator workstation needs the Google Cloud CLI, an authenticated account, a selected
project and region, and permission to manage Cloud Run, Cloud Build, Artifact Registry,
Secret Manager, service accounts, and required IAM bindings.

## Deployment procedure

The following PowerShell sequence is intentionally operator-run. Enabling APIs, creating
cloud resources, generating a real judge key, deploying, and changing IAM are external
mutations and must not be run before the corresponding approval.

```powershell
$UpToCodeProject = "<google-cloud-project-id>"
$UpToCodeRegion = "us-central1"
$UpToCodeHostedHost = "<uptocode-mcp-project-number.region.run.app>"
$UpToCodeCredentialFile = "<absolute-path-outside-repo>\uptocode-production-key.txt"
$UpToCodeDigestFile = "<absolute-path-outside-repo>\uptocode-production-key.sha256"

gcloud config set project $UpToCodeProject
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com
gcloud artifacts repositories create uptocode --repository-format=docker --location=$UpToCodeRegion --description="UpToCode production images"
gcloud iam service-accounts create uptocode-mcp-runtime --display-name="UpToCode MCP runtime"
```

Build once, then deploy the immutable digest rather than a mutable tag:

```powershell
$UpToCodeImageTag = "$UpToCodeRegion-docker.pkg.dev/$UpToCodeProject/uptocode/mcp:v1.0.0"
gcloud builds submit --tag $UpToCodeImageTag .
$UpToCodeDigest = gcloud artifacts docker images describe $UpToCodeImageTag --format="value(image_summary.digest)"
python scripts/render_cloud_run.py --project $UpToCodeProject --region $UpToCodeRegion --image-digest $UpToCodeDigest --host $UpToCodeHostedHost
```

Generate the credential only after explicit key-generation approval. The helper refuses to
write either file inside the repository, uses exclusive creation, and never prints the raw
key or its full digest:

```powershell
python scripts/prepare_judge_credential.py --authorize-key-generation --credential-file $UpToCodeCredentialFile --digest-file $UpToCodeDigestFile
gcloud secrets create uptocode-api-key-hashes --replication-policy=automatic --data-file=$UpToCodeDigestFile
gcloud secrets add-iam-policy-binding uptocode-api-key-hashes --member="serviceAccount:uptocode-mcp-runtime@$UpToCodeProject.iam.gserviceaccount.com" --role="roles/secretmanager.secretAccessor"
```

If the allowlist secret already exists, use `gcloud secrets versions add
uptocode-api-key-hashes --data-file=$UpToCodeDigestFile` instead of recreating it. Keep old
credential material only as long as an intentional overlap is required for rotation.

Validate the rendered manifest before applying it, then deploy:

```powershell
$UpToCodeManifest = ".uptocode/deploy/cloud-run-service.yaml"
gcloud run services replace $UpToCodeManifest --region=$UpToCodeRegion --project=$UpToCodeProject --dry-run
gcloud run services replace $UpToCodeManifest --region=$UpToCodeRegion --project=$UpToCodeProject
$UpToCodeServiceUrl = gcloud run services describe uptocode-mcp --region=$UpToCodeRegion --project=$UpToCodeProject --format="value(status.url)"
```

The template sets `run.googleapis.com/invoker-iam-disabled: "true"` and ingress `all` so
ordinary MCP clients can reach the application bearer boundary. This does not make MCP
requests anonymous: only `/healthz` and `/readyz` bypass the UpToCode key check. Do not add
an `allUsers` IAM binding in parallel.

## Payload-free monitoring

Monitor request counts, HTTP status classes, duration, concurrency, instance count, memory, rule-result counts, judgment request/token totals, and sanitized error classes. Authenticated request logs contain only the first eight hexadecimal characters of the credential's SHA-256 digest as `key_id`; they never contain a raw key or complete digest. Logs and labels must not contain source, excerpts, prompts, authorization headers, keys, email addresses, SSNs, filenames supplied by hosted users, or report bodies.

Configure budget alerts for Cloud Run, Artifact Registry, Secret Manager, and authorized OpenAI usage before traffic is enabled. Treat alert changes as operator-approved infrastructure changes.

## Synthetic health check

- `GET /readyz` must return status and version without authentication or payload data at the public Cloud Run edge. `/healthz` remains the container liveness-probe route; Cloud Run reserves that path on its public edge.
- An authenticated `check_loop` call using only synthetic `while True` code must return AA001.
- A request without a bearer token must return 401.
- A credential exceeding its in-memory token bucket must return 429 with `Retry-After`;
  another credential retains its own independent allowance.
- Hosted tool discovery must not contain `audit_file` or `audit_repo`.
- A hosted request with `judgment=true` must fail while
  `UPTOCODE_HOSTED_JUDGMENT=false` (the default).
- Model judgment smoke is separate, paid, synthetic, and requires explicit authorization
  before setting the global gate to `true`.

Run the no-paid-call live verification with the raw credential loaded from its external
file. The smoke deliberately consumes the configured bucket to prove `429` behavior, so
wait for the returned refill interval before using that key again.

```powershell
$env:UPTOCODE_JUDGE_KEY = (Get-Content -Raw $UpToCodeCredentialFile).Trim()
python scripts/hosted_smoke.py --authorize-live-test --endpoint "$UpToCodeServiceUrl/mcp" --rate-limit 30
```

Export the matching Cloud Run logs and prove that only the short digest prefix appears:

```powershell
$UpToCodeLogFile = "$env:TEMP\uptocode-hosted-logs.json"
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="uptocode-mcp"' --project=$UpToCodeProject --freshness=15m --format=json | Set-Content -Encoding utf8 $UpToCodeLogFile
python scripts/verify_hosted_logs.py --logs $UpToCodeLogFile
Remove-Item Env:UPTOCODE_JUDGE_KEY
```

Also inspect the deployed revision by immutable name, confirm the image digest and
`UPTOCODE_HOSTED_JUDGMENT=false`, and retain the sanitized smoke/log evidence outside the
repository for operations. Never retain raw Cloud Run log exports in Git.

After every live check passes, add the exact `https://.../mcp` URL to `server.json` as a
`streamable-http` remote, update the website and claims to state that the hosted endpoint
exists, and rerun the complete production gate before creating `v1.0.0`.

## MCP SDK upgrade canary

UpToCode pins `mcp==1.28.1` because strict unknown-argument rejection currently requires
a guarded FastMCP private contract. `tests/test_mcp_hardening.py` is the upgrade canary: it
asserts the installed SDK version, exercises the private contract, and confirms every tool
still advertises `additionalProperties: false`. At runtime, any missing private attribute
fails server construction with an error that names the installed MCP SDK version.

To evaluate an SDK upgrade:

1. Work on a separate branch; do not relax or delete `_harden_tool_contracts`.
2. Change the exact `mcp` pin and `MCP_FASTMCP_COMPAT_VERSION` together.
3. Run `python -m pytest -q tests/test_mcp_hardening.py tests/test_mcp_server.py
   tests/test_hosted_lifecycle.py`.
4. Inspect every local and hosted tool schema for `additionalProperties: false`, then run
   the full Submission-Ready Gate on Windows and POSIX.
5. If FastMCP internals changed, adapt the guarded compatibility layer and its malformed-SDK
   test in the same commit. Do not ship an unguarded fallback or `extra="ignore"` behavior.

## CI and composite Action operations

The nine Python compatibility cells never perform dependency auditing. The dedicated audit
job builds the application wheel, creates an isolated environment, upgrades pip,
setuptools, and wheel there, installs the wheel plus its dependencies, then runs `pip check`
and `pip-audit`. This keeps an environment-specific audit defect from obscuring compatibility
test results.

Every CI job has a timeout and branch/ref concurrency cancellation. Artifacts retain matrix
coverage/compliance evidence, the application wheel, distributions, Python and site SBOMs,
and SARIF. The container smoke must prove `/healthz` 200, unauthenticated `/mcp` 401, and a
bounded clean shutdown. Site CI must run ESLint, `tsc --noEmit`, the production build, and
both rendered-route tests.

The root `action.yml` defaults to `version: source`. Its scan step captures and neutralizes
the scanner exit temporarily, the SARIF upload uses `always()`, and the final step returns
the captured code. A caller enabling SARIF upload grants `security-events: write`.
Published semantic-version installation becomes available only after the separately
approved PyPI release succeeds.

## Rollback

1. Route all traffic back to the last known-good Cloud Run revision by immutable revision name.
2. Disable the failed revision; do not debug using customer payloads.
3. Rotate private-beta keys if authorization or log handling is implicated.
4. Preserve only payload-free platform logs, image digest, compliance artifact, SBOM, metrics, and sanitized error class for incident review.
5. Re-run the hosted lifecycle, no-persistence, log-capture, and compliance gates before promoting a corrected revision.
