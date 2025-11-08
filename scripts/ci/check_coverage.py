#!/usr/bin/env python3
"""Coverage policy enforcement for Story 4.7.

Usage (after running pytest with --cov-report=json:coverage.json):
    python scripts/ci/check_coverage.py coverage.json \
        --baseline-file docs/coverage-baseline.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _extract_percent_from_coverage(payload: dict) -> float:
    totals = payload.get("totals")
    if not isinstance(totals, dict):
        raise ValueError("coverage JSON is missing 'totals.percent_covered'")
    percent = totals.get("percent_covered")
    if percent is None:
        raise ValueError("coverage JSON does not contain percent_covered")
    return float(percent)


def _read_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _read_baseline_from_file(path: Path) -> float:
    payload = _read_json(path)
    for key in ("overall_percent", "percent", "coverage"):
        if key in payload:
            return float(payload[key])
    raise ValueError(
        f"Baseline file {path} is missing 'overall_percent' (found keys: {list(payload)})"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare coverage results against policy."
    )
    parser.add_argument("coverage_json", type=Path, help="Path to coverage JSON report")
    parser.add_argument(
        "--baseline-file",
        type=Path,
        help="JSON file that records the baseline overall percent (overall_percent key)",
    )
    parser.add_argument(
        "--baseline",
        type=float,
        help="Override baseline percentage (used by CI when baseline_file is unavailable)",
    )
    parser.add_argument(
        "--max-regression",
        type=float,
        default=5.0,
        help="Maximum allowed regression vs baseline before failing (percent points)",
    )
    parser.add_argument(
        "--warn-threshold",
        type=float,
        default=75.0,
        help="Warn (but do not fail) when coverage drops below this percent",
    )

    args = parser.parse_args()

    coverage_payload = _read_json(args.coverage_json)
    measured_percent = _extract_percent_from_coverage(coverage_payload)

    baseline_percent: float
    if args.baseline is not None:
        baseline_percent = float(args.baseline)
    elif args.baseline_file is not None:
        baseline_percent = _read_baseline_from_file(args.baseline_file)
    else:
        baseline_percent = measured_percent

    regression = baseline_percent - measured_percent
    status_messages = [
        f"[coverage] measured={measured_percent:.2f}%",
        f"baseline={baseline_percent:.2f}%",
        f"regression={regression:.2f}pp",
    ]
    print(" ".join(status_messages))

    if regression > args.max_regression:
        print(
            f"[coverage] ERROR: regression {regression:.2f}pp exceeds "
            f"limit of {args.max_regression:.2f}pp",
            file=sys.stderr,
        )
        return 1

    if measured_percent < args.warn_threshold:
        print(
            f"[coverage] WARNING: overall coverage {measured_percent:.2f}% "
            f"is below the {args.warn_threshold:.2f}% project target",
            file=sys.stderr,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
