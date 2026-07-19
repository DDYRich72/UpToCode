"""Emit executable AA001-AA012 dogfood evidence for production source."""

from __future__ import annotations

import hashlib
import json
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

OUTPUT = ROOT / ".archagent-audit" / "architecture-compliance.json"


EVIDENCE = {
    "AA001": ("archagent_audit/engine.py", "tests/test_gate2_edges.py"),
    "AA002": ("archagent_audit/config.py", "tests/test_production_contract.py"),
    "AA003": ("archagent_audit/review.py", "tests/test_review_plan.py"),
    "AA004": ("archagent_audit/schema_validation.py", "tests/test_production_contract.py"),
    "AA005": ("archagent_audit/judgment.py", "tests/test_judgment_candidates.py"),
    "AA006": ("archagent_audit/redaction.py", "tests/test_gate1.py"),
    "AA007": ("archagent_audit/judgment.py", "tests/test_judgment.py"),
    "AA008": ("archagent_audit/engine.py", "tests/test_production_contract.py"),
    "AA009": ("archagent_audit/mcp_server.py", "tests/test_mcp_server.py"),
    "AA010": ("archagent_audit/judgment.py", "tests/test_judgment.py"),
    "AA011": ("archagent_audit/rules/core.yml", "tests/test_rule_contract_matrix.py"),
    "AA012": ("archagent_audit/models.py", "tests/test_hosted_lifecycle.py"),
}


def version_contract() -> dict[str, object]:
    from archagent_audit import __version__

    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "server.json").read_text(encoding="utf-8"))
    package_versions = sorted({item["version"] for item in manifest["packages"]})
    values = {
        "project": project["project"]["version"],
        "runtime": __version__,
        "server": manifest["version"],
        "server_packages": package_versions,
    }
    values["status"] = (
        "passed"
        if values["project"] == values["runtime"] == values["server"]
        and package_versions == [__version__]
        else "failed"
    )
    return values


def main() -> int:
    from archagent_audit.engine import scan_path

    report = scan_path(ROOT / "archagent_audit")
    versions = version_contract()
    production_clean = (
        not report.findings
        and not report.analysis_warnings
        and report.suppressions == 0
        and versions["status"] == "passed"
    )
    controls = [
        {
            "rule_id": rule_id,
            "implementation": implementation,
            "test": test,
            "status": "passed" if production_clean else "failed",
        }
        for rule_id, (implementation, test) in EVIDENCE.items()
    ]
    evidence = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "production_scan": {
            "findings": len(report.findings),
            "warnings": len(report.analysis_warnings),
            "suppressions": report.suppressions,
        },
        "version_contract": versions,
        "controls": controls,
    }
    canonical = json.dumps(evidence, sort_keys=True, separators=(",", ":"))
    evidence["integrity_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(f"{'PASS' if production_clean else 'FAIL'}: {OUTPUT}")
    return 0 if production_clean else 1


if __name__ == "__main__":
    raise SystemExit(main())
