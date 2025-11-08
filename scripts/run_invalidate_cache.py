#!/usr/bin/env python3
"""Manual runner for the invalidate_cache MCP tool."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from canary_mcp.server import invalidate_cache  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Invalidate cache entries via the MCP invalidate_cache tool."
    )
    parser.add_argument(
        "--pattern",
        default="",
        help="Optional SQL-like pattern to match cache keys (empty = all).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = invalidate_cache(pattern=args.pattern)
    print("=== invalidate_cache ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
