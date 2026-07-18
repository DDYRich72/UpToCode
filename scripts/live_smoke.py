"""One-request GPT-5.6 smoke test. Run only after explicit paid-use approval."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from openai import OpenAI

from archagent_audit.judgment import run_judgment
from archagent_audit.judgment_candidates import JudgmentCandidate
from archagent_audit.models import Coverage, Report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--authorize-cost",
        action="store_true",
        help="Confirm that one paid GPT-5.6 request is authorized.",
    )
    arguments = parser.parse_args()
    if not arguments.authorize_cost:
        parser.error("--authorize-cost is required")
    if not os.environ.get("OPENAI_API_KEY"):
        parser.error("OPENAI_API_KEY is required")

    report = Report(
        scan_root="<synthetic-live-smoke>",
        coverage=Coverage(files_discovered=1, files_analyzed=1),
    )
    candidate = JudgmentCandidate(
        rule_id="AA009",
        file="synthetic_tool.py",
        line=2,
        evidence="Synthetic function-tool schema requires semantic quality review.",
        excerpt="@function_tool\ndef do(value): ...",
    )
    client = OpenAI(max_retries=0, timeout=30.0)
    run_judgment(report, [candidate], client=client)
    passed = report.judgment_status == "completed"
    evidence = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": "gpt-5.6",
        "request_count": 1,
        "synthetic_code_only": True,
        "status": report.judgment_status,
        "finding_count": len(report.findings),
        "analysis_warning_codes": [item.code for item in report.analysis_warnings],
        "pass": passed,
    }
    output = Path(".archagent-audit/live-smoke.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(f"{'PASS' if passed else 'FAIL'}: one-request GPT-5.6 smoke; evidence: {output}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
