# Feature Spec: UpToCode Production Identity and Release

## Purpose

Complete the post-event production train under one canonical identity before the first
public package and MCP Registry release.

## User story

As a developer, I want every install, command, report, MCP connection, hosted endpoint,
and document to identify the product as UpToCode, so that the product has one clear name.

## Scope

### In scope

- Rename the distribution, import package, CLI, local state/configuration paths,
  environment variables, report branding, GitHub Action, site, and documentation.
- Adopt `io.github.DDYRich72/uptocode` as the official MCP Registry identity.
- Prepare a tag-driven trusted-publishing workflow with build verification, SBOMs,
  attestations, and a protected `pypi` environment.
- Prepare and verify an immutable `uptocode-mcp` Cloud Run deployment.
- Publish the final package and registry record only after explicit operator checkpoints.
- Add separate 1.1 specifications for beta access control and TypeScript analysis.

### Out of scope

- Rewriting Git history or historical tags.
- Publishing compatibility aliases using the superseded product name.
- Changing AA001–AA012 semantics or report-version compatibility.
- Enabling hosted judgment or making a paid model call without explicit approval.
- Implementing Firestore or TypeScript in this phase.

## Functional requirements

1. `pip install uptocode`, `import uptocode`, `python -m uptocode`, and the `uptocode`
   console command resolve to the same versioned application.
2. Public files and generated output use UpToCode naming and `UPTOCODE_*` settings.
3. Local and hosted MCP instructions identify the server as UpToCode; the registry
   manifest name is `io.github.DDYRich72/uptocode`.
4. Package metadata, runtime version, and `server.json` agree.
5. Release automation builds once, verifies artifacts, emits SBOMs and attestations,
   and publishes through GitHub OIDC only from an approved production tag.
6. The new hosted service preserves authentication, containment, rate limiting,
   default-off judgment, payload-free logs, and graceful shutdown.

## Safety requirements

- Keep static analysis offline and preserve double consent for judgment.
- Never print, commit, or migrate raw credentials through repository content.
- Stop before package publication, repository visibility changes, deployment, registry
  submission, key distribution, or a paid model call unless explicitly approved.
- Preserve the frozen `v1.0.0-submission` tag.

## Acceptance criteria

- [x] No current tracked product surface contains the superseded identity except an
  explicitly labeled historical migration note.
- [x] Full Windows and POSIX gates pass with at least 85% branch coverage.
- [x] A clean wheel environment installs and executes `uptocode` successfully.
- [x] Site lint, type check, build, tests, and production dependency audit pass.
- [x] Container health, unauthorized MCP, authenticated discovery, rate-limit,
  judgment-off, log-safety, and shutdown checks pass for `uptocode-mcp`.
- [x] Package, runtime, manifest, and generated report version checks pass.
- [x] Trusted-publishing workflow and MCP manifest validate before approved publication.
- [x] 1.1 beta-access and TypeScript specifications exist without implementation.
- [x] Claims and validation evidence are synchronized and the working tree is clean.

## Test plan

- Unit/integration: update the complete Python and site suites for canonical identifiers.
- Packaging: build sdist/wheel, inspect metadata, install into an isolated environment,
  run version/help/self-scan/MCP discovery.
- Deployment: render the immutable manifest and run local container lifecycle checks;
  run live checks only after deployment approval.
- Publication: validate workflow YAML and artifact contents before OIDC publish, then
  verify the public distributions, attestations, and registry record after approval.
