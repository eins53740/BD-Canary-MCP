#!/usr/bin/env python3
"""Manual runner for the write_test_dataset MCP tool (dry run by default)."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from canary_mcp.server import write_test_dataset  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the write_test_dataset tool.")
    parser.add_argument(
        "--dataset",
        default="Test/Maceira",
        help="Target dataset (must start with Test/).",
    )
    parser.add_argument(
        "--tag",
        default="Test/Maceira/MCP.Audit.Success",
        help="Historian tag for the synthetic record.",
    )
    parser.add_argument(
        "--value",
        type=float,
        default=1.0,
        help="Numeric value to write (default: %(default)s).",
    )
    parser.add_argument(
        "--timestamp",
        default=datetime.utcnow().isoformat() + "Z",
        help="ISO timestamp for the record.",
    )
    parser.add_argument(
        "--role",
        default="tester",
        help="Tester role name (must belong to CANARY_TESTER_ROLES).",
    )
    parser.add_argument(
        "--original-prompt",
        default="Manual write_test_dataset smoke run",
        help="Natural-language prompt stored for auditing.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Perform a real write instead of the default dry run.",
    )
    parser.add_argument(
        "--records-file",
        help="Path to a JSON file defining the records list (overrides --tag/--value).",
    )
    return parser.parse_args()


def build_records(args: argparse.Namespace) -> list[dict[str, Any]]:
    if args.records_file:
        path = Path(args.records_file)
        if not path.exists():
            raise FileNotFoundError(f"{path} does not exist")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError("Records file must contain a JSON array of records")
        return payload

    return [
        {
            "tag": args.tag,
            "value": args.value,
            "timestamp": args.timestamp,
        }
    ]


async def main() -> int:
    args = parse_args()
    records = build_records(args)
    result = await write_test_dataset.fn(
        dataset=args.dataset,
        records=records,
        original_prompt=args.original_prompt,
        role=args.role,
        dry_run=not args.execute,
    )
    print("=== write_test_dataset ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
