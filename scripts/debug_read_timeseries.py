#!/usr/bin/env python3
"""Ad-hoc harness for inspecting read_timeseries MCP requests and responses."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

# Ensure repository src/ is on the import path
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from canary_mcp.server import read_timeseries  # type: ignore  # noqa: E402


def _isoformat_utc(dt: datetime) -> str:
    """Format a datetime as an ISO8601 string with trailing Z."""
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _default_time_range() -> tuple[str, str]:
    """Return a (start, end) tuple covering the past hour."""
    end_dt = datetime.now(timezone.utc)
    start_dt = end_dt - timedelta(hours=1)
    return _isoformat_utc(start_dt), _isoformat_utc(end_dt)


def _install_httpx_probe() -> None:
    """Monkey-patch httpx.AsyncClient.post to log outgoing JSON payloads."""
    original_post = httpx.AsyncClient.post

    async def debug_post(
        self: httpx.AsyncClient,
        url: str,
        *args: Any,
        **kwargs: Any,
    ) -> httpx.Response:
        json_payload = kwargs.get("json")
        print("─" * 80)
        print(f"POST {url}")
        if json_payload is not None:
            serialized = json.dumps(json_payload, indent=2, ensure_ascii=False)
            print("Request payload:")
            print(serialized)
        else:
            print("Request payload: <none>")

        response = await original_post(self, url, *args, **kwargs)

        print(f"Status: {response.status_code}")
        try:
            data = response.json()
        except ValueError:
            print("Response is not JSON decodable. Raw text follows:")
            print(response.text)
        else:
            serialized_response = json.dumps(data, indent=2, ensure_ascii=False)
            if len(serialized_response) > 4_000:
                print("Response JSON (truncated to 4000 chars):")
                print(serialized_response[:4000] + " …")
            else:
                print("Response JSON:")
                print(serialized_response)

        return response

    httpx.AsyncClient.post = debug_post  # type: ignore[assignment]


async def _run(args: argparse.Namespace) -> None:
    """Execute read_timeseries.fn with logging enabled."""
    _install_httpx_probe()

    if args.raw_string:
        tag_arg: str | list[str] = args.tags[0]
    else:
        tag_arg = args.tags[0] if len(args.tags) == 1 else list(args.tags)

    result = await read_timeseries.fn(
        tag_arg,
        start_time=args.start,
        end_time=args.end,
        views=args.views or None,
        page_size=args.page_size,
    )

    print("─" * 80)
    print("read_timeseries result:")
    print(json.dumps(result, indent=2, ensure_ascii=False))


def parse_args() -> argparse.Namespace:
    start_default, end_default = _default_time_range()

    parser = argparse.ArgumentParser(
        description="Debug the read_timeseries MCP tool by printing underlying HTTP interactions."
    )
    parser.add_argument(
        "tags",
        nargs="+",
        help=(
            "One or more tag identifiers. Provide multiple values to send a list. "
            "Use --raw-string to send the first argument exactly as written."
        ),
    )
    parser.add_argument(
        "--start",
        default=start_default,
        help=f"Start time (ISO or Canary relative). Default: {start_default}",
    )
    parser.add_argument(
        "--end",
        default=end_default,
        help=f"End time (ISO or Canary relative). Default: {end_default}",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=1000,
        help="Page size for Canary getTagData (default 1000).",
    )
    parser.add_argument(
        "--view",
        dest="views",
        action="append",
        default=[],
        help="Optional Canary view name. Can be provided multiple times.",
    )
    parser.add_argument(
        "--raw-string",
        action="store_true",
        help="Send the first positional tag argument as a raw string (useful for testing JSON arrays).",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        asyncio.run(_run(args))
    except KeyboardInterrupt:
        print("\nInterrupted by user.")


if __name__ == "__main__":
    main()
