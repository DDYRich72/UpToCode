"""Verify exported hosted logs contain attribution but no submitted payload or key."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SMOKE = ROOT / ".uptocode" / "hosted-smoke.json"
DEFAULT_OUTPUT = ROOT / ".uptocode" / "hosted-log-safety.json"


def verify_logs(*, logs: str, smoke: dict[str, object], credential: str) -> dict[str, object]:
    """Fail if exported logs contain forbidden values or omit safe key attribution."""
    digest = hashlib.sha256(credential.encode("utf-8")).hexdigest()
    prefix = digest[:8]
    sentinel = str(smoke.get("synthetic_sentinel", ""))
    if not sentinel:
        raise ValueError("smoke evidence does not contain a synthetic sentinel")
    forbidden = {
        "raw_credential": credential,
        "full_credential_digest": digest,
        "submitted_sentinel": sentinel,
    }
    leaked = [name for name, value in forbidden.items() if value in logs]
    if leaked:
        raise ValueError(f"hosted logs contain forbidden values: {', '.join(leaked)}")
    if f"key_id={prefix}" not in logs:
        raise ValueError("hosted logs do not contain the expected safe key_id prefix")
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "key_id": prefix,
        "safe_key_attribution": "passed",
        "raw_credential_absent": "passed",
        "full_digest_absent": "passed",
        "submitted_sentinel_absent": "passed",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check payload-free Cloud Run log export.")
    parser.add_argument("--logs", type=Path, required=True)
    parser.add_argument("--smoke", type=Path, default=DEFAULT_SMOKE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    credential = os.environ.get("UPTOCODE_JUDGE_KEY", "")
    if not credential:
        parser.error("UPTOCODE_JUDGE_KEY is required")
    try:
        logs = arguments.logs.read_text(encoding="utf-8")
        smoke = json.loads(arguments.smoke.read_text(encoding="utf-8"))
        evidence = verify_logs(logs=logs, smoke=smoke, credential=credential)
        output = arguments.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, json.JSONDecodeError) as error:
        parser.error(str(error))
    print(f"PASS: hosted logs are payload-free; evidence: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
