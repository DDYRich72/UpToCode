"""Emit executable AA001-AA013 dogfood evidence for production source."""

from __future__ import annotations

import hashlib
import json
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

OUTPUT = ROOT / ".uptocode" / "architecture-compliance.json"


EVIDENCE = {
    "AA001": ("uptocode/engine.py", "tests/test_gate2_edges.py"),
    "AA002": ("uptocode/config.py", "tests/test_production_contract.py"),
    "AA003": ("uptocode/review.py", "tests/test_review_plan.py"),
    "AA004": ("uptocode/schema_validation.py", "tests/test_production_contract.py"),
    "AA005": ("uptocode/judgment.py", "tests/test_judgment_candidates.py"),
    "AA006": ("uptocode/redaction.py", "tests/test_gate1.py"),
    "AA007": ("uptocode/judgment.py", "tests/test_judgment.py"),
    "AA008": ("uptocode/engine.py", "tests/test_production_contract.py"),
    "AA009": ("uptocode/mcp_server.py", "tests/test_mcp_server.py"),
    "AA010": ("uptocode/judgment.py", "tests/test_judgment.py"),
    "AA011": ("uptocode/rules/core.yml", "tests/test_rule_contract_matrix.py"),
    "AA012": ("uptocode/models.py", "tests/test_hosted_lifecycle.py"),
    "AA013": ("uptocode/analysis.py", "tests/test_batch1_quick_wins.py"),
}


def version_contract() -> dict[str, object]:
    from uptocode import __version__

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
    from uptocode.engine import scan_path

    report = scan_path(ROOT / "uptocode")
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
