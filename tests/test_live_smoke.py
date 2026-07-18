from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_live_smoke_refuses_without_explicit_cost_authorization() -> None:
    environment = dict(os.environ)
    environment.pop("OPENAI_API_KEY", None)

    result = subprocess.run(
        [sys.executable, "scripts/live_smoke.py"],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    assert result.returncode == 2
    assert "--authorize-cost is required" in result.stderr
