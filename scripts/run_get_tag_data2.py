#!/usr/bin/env python3
"""Manual runner for the get_tag_data2 MCP tool."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from canary_mcp.server import get_tag_data2  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the get_tag_data2 tool to inspect historical samples."
    )
    parser.add_argument(
        "--tags",
        default="Maceira.Cement.Kiln6.Temperature.Outlet",
        help="Comma-separated list of tag paths (default: %(default)s).",
    )
    parser.add_argument(
        "--start-time",
        default=(datetime.utcnow() - timedelta(minutes=30)).isoformat() + "Z",
        help="Start timestamp (ISO or relative expression).",
    )
    parser.add_argument(
        "--end-time",
        default=datetime.utcnow().isoformat() + "Z",
        help="End timestamp (ISO or relative expression).",
    )
    parser.add_argument(
        "--aggregate-name",
        help="Optional aggregate function (e.g., TimeAverage2).",
    )
    parser.add_argument(
        "--aggregate-interval",
        help="Optional aggregate interval (e.g., 00:05:00).",
    )
    parser.add_argument(
        "--max-size",
        type=int,
        default=1000,
        help="Max samples per request (default: %(default)s).",
    )
    return parser.parse_args()


async def main() -> int:
    args = parse_args()
    tag_list = [tag.strip() for tag in args.tags.split(",") if tag.strip()]

    result = await get_tag_data2.fn(
        tag_names=tag_list,
        start_time=args.start_time,
        end_time=args.end_time,
        aggregate_name=args.aggregate_name,
        aggregate_interval=args.aggregate_interval,
        max_size=args.max_size,
    )

    print("=== get_tag_data2 ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
