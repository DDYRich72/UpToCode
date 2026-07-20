"""Render the reviewed Cloud Run template without deploying it."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "deploy" / "cloud-run-service.yaml"
DEFAULT_OUTPUT = ROOT / ".archagent-audit" / "deploy" / "cloud-run-service.yaml"
PROJECT_PATTERN = re.compile(r"[a-z][a-z0-9-]{4,28}[a-z0-9]")
REGION_PATTERN = re.compile(r"[a-z][a-z0-9-]*[a-z0-9]")
DIGEST_PATTERN = re.compile(r"sha256:[0-9a-f]{64}")
HOST_PATTERN = re.compile(r"[a-z0-9][a-z0-9.-]*[a-z0-9]")


def render_template(*, project: str, region: str, image_digest: str, host: str) -> str:
    """Return a validated, secret-free service manifest pinned to an image digest."""
    if not PROJECT_PATTERN.fullmatch(project):
        raise ValueError("project must be a valid lowercase Google Cloud project ID")
    if not REGION_PATTERN.fullmatch(region):
        raise ValueError("region must be a valid lowercase Google Cloud region")
    if not DIGEST_PATTERN.fullmatch(image_digest):
        raise ValueError("image_digest must be sha256 followed by 64 lowercase hex characters")
    if not HOST_PATTERN.fullmatch(host) or "://" in host or "/" in host:
        raise ValueError("host must be a bare lowercase DNS host name")

    rendered = (
        TEMPLATE.read_text(encoding="utf-8")
        .replace("REGION", region)
        .replace("PROJECT", project)
        .replace("IMAGE_DIGEST", image_digest)
        .replace("PUBLIC_DNS_VALUE", host)
    )
    document = yaml.safe_load(rendered)
    container = document["spec"]["template"]["spec"]["containers"][0]
    environment = {item["name"] for item in container["env"]}
    annotations = document["metadata"]["annotations"]

    expected_image = f"{region}-docker.pkg.dev/{project}/archagent/mcp@{image_digest}"
    if container["image"] != expected_image:
        raise ValueError("rendered image reference is not the expected immutable digest")
    if "OPENAI_API_KEY" in environment:
        raise ValueError("hosted judgment is disabled, so OPENAI_API_KEY must not be attached")
    allowed_hosts = {item["name"]: item for item in container["env"]}
    if allowed_hosts["ARCHAGENT_HOSTED_ALLOWED_HOSTS"]["value"] != host:
        raise ValueError("rendered hosted allowlist is not the expected host")
    if annotations.get("run.googleapis.com/invoker-iam-disabled") != "true":
        raise ValueError("Cloud Run IAM must yield authentication to the application bearer key")
    if any(
        token in rendered
        for token in ("REGION", "PROJECT", "IMAGE_DIGEST", "PUBLIC_DNS_VALUE")
    ):
        raise ValueError("unresolved deployment placeholder")
    return rendered


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render a Cloud Run service manifest; this command never deploys.",
    )
    parser.add_argument("--project", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--image-digest", required=True)
    parser.add_argument("--host", required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()

    try:
        rendered = render_template(
            project=arguments.project,
            region=arguments.region,
            image_digest=arguments.image_digest,
            host=arguments.host,
        )
        output = arguments.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(f"Rendered deployment manifest: {output}")
    print("No deployment or credential operation was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
