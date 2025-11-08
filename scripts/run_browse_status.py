#!/usr/bin/env python3
"""Manual runner for the browse_status MCP tool."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from canary_mcp.server import browse_status  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the browse_status tool.")
    parser.add_argument(
        "--path",
        help="Namespace path to start browsing from (e.g., Secil.Portugal).",
    )
    parser.add_argument(
        "--depth",
        type=int,
        help="Depth for tree expansion (default: server-side default).",
    )
    parser.add_argument(
        "--no-tags",
        dest="include_tags",
        action="store_false",
        help="Exclude tags from the response.",
    )
    parser.add_argument(
        "--view",
        help="Optional Canary view (maps to the views query parameter).",
    )
    parser.set_defaults(include_tags=True)
    return parser.parse_args()


async def main() -> int:
    args = parse_args()
    result = await browse_status.fn(
        path=args.path,
        depth=args.depth,
        include_tags=args.include_tags,
        view=args.view,
    )
    print("=== browse_status ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
