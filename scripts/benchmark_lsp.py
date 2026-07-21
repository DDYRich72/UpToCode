"""Measure the persistent language server's warm file-analysis hot path."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
import time

from uptocode.engine import AuditService


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=Path("fixtures/lsp/typical_agent.py"),
    )
    parser.add_argument("--budget-ms", type=float, default=200.0)
    parser.add_argument("--iterations", type=int, default=20)
    args = parser.parse_args()
    service = AuditService()
    service.scan(args.path)
    measurements: list[float] = []
    for _ in range(args.iterations):
        started = time.perf_counter()
        service.scan(args.path)
        measurements.append((time.perf_counter() - started) * 1_000)
    ordered = sorted(measurements)
    p95 = ordered[max(0, min(len(ordered) - 1, round(0.95 * len(ordered) + 0.5) - 1))]
    print(
        json.dumps(
            {
                "iterations": len(measurements),
                "median_ms": round(statistics.median(measurements), 2),
                "p95_ms": round(p95, 2),
                "budget_ms": args.budget_ms,
                "pass": p95 < args.budget_ms,
            },
            sort_keys=True,
        )
    )
    return 0 if p95 < args.budget_ms else 1


if __name__ == "__main__":
    raise SystemExit(main())
