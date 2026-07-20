from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from scripts.prepare_judge_credential import validate_destination
from scripts.render_cloud_run import render_template
from scripts.verify_hosted_logs import verify_logs


ROOT = Path(__file__).parents[1]


def test_cloud_run_template_is_safe_for_application_bearer_auth() -> None:
    template = yaml.safe_load(
        (ROOT / "deploy" / "cloud-run-service.yaml").read_text(encoding="utf-8")
    )
    annotations = template["metadata"]["annotations"]
    container = template["spec"]["template"]["spec"]["containers"][0]
    environment = {item["name"]: item for item in container["env"]}

    assert annotations["run.googleapis.com/invoker-iam-disabled"] == "true"
    assert annotations["run.googleapis.com/ingress"] == "all"
    assert container["image"].endswith("@IMAGE_DIGEST")
    assert environment["UPTOCODE_HOSTED_JUDGMENT"]["value"] == "false"
    assert environment["UPTOCODE_HOSTED_ALLOWED_HOSTS"]["value"] == "PUBLIC_DNS_VALUE"
    assert "OPENAI_API_KEY" not in environment
    assert environment["UPTOCODE_API_KEY_HASHES"]["valueFrom"]["secretKeyRef"]


def test_cloud_run_renderer_pins_the_exact_image_and_resolves_placeholders() -> None:
    digest = "sha256:" + "a" * 64
    rendered = render_template(
        project="uptocode-demo1",
        region="us-central1",
        image_digest=digest,
        host="uptocode-mcp.example.run.app",
    )
    manifest = yaml.safe_load(rendered)
    image = manifest["spec"]["template"]["spec"]["containers"][0]["image"]

    assert image == f"us-central1-docker.pkg.dev/uptocode-demo1/uptocode/mcp@{digest}"
    assert not any(
        token in rendered
        for token in ("REGION", "PROJECT", "IMAGE_DIGEST", "PUBLIC_DNS_VALUE")
    )


@pytest.mark.parametrize(
    ("project", "region", "digest"),
    [
        ("UPPERCASE", "us-central1", "sha256:" + "a" * 64),
        ("uptocode-demo1", "bad_region", "sha256:" + "a" * 64),
        ("uptocode-demo1", "us-central1", "latest"),
    ],
)
def test_cloud_run_renderer_rejects_mutable_or_malformed_coordinates(
    project: str,
    region: str,
    digest: str,
) -> None:
    with pytest.raises(ValueError):
        render_template(
            project=project,
            region=region,
            image_digest=digest,
            host="uptocode-mcp.example.run.app",
        )


def test_cloud_run_renderer_rejects_a_host_url_instead_of_a_bare_host() -> None:
    with pytest.raises(ValueError, match="bare lowercase DNS host"):
        render_template(
            project="uptocode-demo1",
            region="us-central1",
            image_digest="sha256:" + "a" * 64,
            host="https://uptocode-mcp.example.run.app/mcp",
        )


def test_server_manifest_uses_the_canonical_registry_and_package_identity() -> None:
    manifest = json.loads((ROOT / "server.json").read_text(encoding="utf-8"))

    assert manifest["name"] == "io.github.DDYRich72/uptocode"
    assert manifest["title"] == "UpToCode"
    assert manifest["repository"] == {
        "url": "https://github.com/DDYRich72/UpToCode",
        "source": "github",
        "id": "1305781548",
    }
    assert manifest["packages"] == [
        {
            "registryType": "pypi",
            "identifier": "uptocode",
            "version": "1.0.0",
            "runtimeHint": "uvx",
            "packageArguments": [
                {"type": "positional", "value": "serve"},
                {"type": "named", "name": "--transport", "value": "stdio"},
            ],
            "transport": {"type": "stdio"},
        }
    ]
    remote = manifest["remotes"][0]
    assert remote["type"] == "streamable-http"
    assert remote["url"] == (
        "https://uptocode-mcp-1015314816960.us-central1.run.app/mcp"
    )
    assert remote["headers"][0]["value"] == "Bearer {UPTOCODE_API_KEY}"
    assert "<!-- mcp-name: io.github.DDYRich72/uptocode -->" in (
        ROOT / "README.md"
    ).read_text(encoding="utf-8")


def test_credential_destination_must_be_outside_repository(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="outside the repository"):
        validate_destination(ROOT / ".uptocode" / "judge-key.txt")
    assert validate_destination(tmp_path / "judge-key.txt") == (tmp_path / "judge-key.txt").resolve()


def test_credential_generator_refuses_without_authorization(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/prepare_judge_credential.py",
            "--credential-file",
            str(tmp_path / "judge-key.txt"),
            "--digest-file",
            str(tmp_path / "judge-key.sha256"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    assert result.returncode == 2
    assert "--authorize-key-generation is required" in result.stderr
    assert not list(tmp_path.iterdir())


def test_hosted_smoke_refuses_without_live_authorization() -> None:
    environment = dict(os.environ)
    environment.pop("UPTOCODE_JUDGE_KEY", None)
    result = subprocess.run(
        [
            sys.executable,
            "scripts/hosted_smoke.py",
            "--endpoint",
            "https://example.invalid/mcp",
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    assert result.returncode == 2
    assert "--authorize-live-test is required" in result.stderr


def test_hosted_log_verifier_accepts_only_safe_prefix_attribution() -> None:
    credential = "synthetic-judge-key"
    digest = hashlib.sha256(credential.encode("utf-8")).hexdigest()
    smoke = {"synthetic_sentinel": "phase5-sentinel@example.invalid"}
    logs = json.dumps({"textPayload": f"request complete key_id={digest[:8]} status=200"})

    evidence = verify_logs(logs=logs, smoke=smoke, credential=credential)

    assert evidence["safe_key_attribution"] == "passed"
    with pytest.raises(ValueError, match="submitted_sentinel"):
        verify_logs(
            logs=logs + " phase5-sentinel@example.invalid",
            smoke=smoke,
            credential=credential,
        )
