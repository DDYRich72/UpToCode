from __future__ import annotations

import json
import tomllib
from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_source_distribution_is_limited_to_public_package_material() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    included = set(project["tool"]["hatch"]["build"]["targets"]["sdist"]["include"])

    assert included == {
        "/CHANGELOG.md",
        "/LICENSE",
        "/README.md",
        "/SECURITY.md",
        "/pyproject.toml",
        "/server.json",
        "/uptocode",
    }
    assert not {"/web", "/docs", "/tests", "/.claude"} & included


def test_public_identity_is_consistent_across_package_and_mcp_manifest() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "server.json").read_text(encoding="utf-8"))
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert project["project"]["name"] == "uptocode"
    assert project["project"]["scripts"] == {"uptocode": "uptocode.cli:app"}
    assert manifest["name"] == "io.github.DDYRich72/uptocode"
    assert manifest["packages"][0]["identifier"] == "uptocode"
    assert manifest["remotes"] == [
        {
            "type": "streamable-http",
            "url": "https://uptocode-mcp-1015314816960.us-central1.run.app/mcp",
            "headers": [
                {
                    "name": "Authorization",
                    "value": "Bearer {UPTOCODE_API_KEY}",
                    "variables": {
                        "UPTOCODE_API_KEY": {
                            "description": (
                                "Private-beta credential supplied separately by the "
                                "UpToCode operator."
                            ),
                            "isRequired": True,
                            "isSecret": True,
                        }
                    },
                }
            ],
        }
    ]
    assert "mcp-name: io.github.DDYRich72/uptocode" in readme
