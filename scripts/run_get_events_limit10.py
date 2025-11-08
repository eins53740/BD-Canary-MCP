#!/usr/bin/env python3
"""Manual runner for the get_events_limit10 MCP tool."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from canary_mcp.server import get_events_limit10  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the get_events_limit10 tool for Canary event diagnostics."
    )
    parser.add_argument("--limit", type=int, default=10, help="Number of events to return.")
    parser.add_argument(
        "--view",
        default=os.getenv("CANARY_EVENTS_VIEW"),
        help="Optional Canary view name to scope the query (CANARY_EVENTS_VIEW).",
    )
    parser.add_argument(
        "--start-time",
        help="ISO timestamp or Canary relative expression (default: not provided).",
    )
    parser.add_argument(
        "--end-time",
        help="ISO timestamp or Canary relative expression (default: not provided).",
    )
    return parser.parse_args()


async def main() -> int:
    args = parse_args()
    result = await get_events_limit10.fn(
        limit=args.limit,
        view=args.view,
        start_time=args.start_time,
        end_time=args.end_time,
    )

    print("=== get_events_limit10 ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
