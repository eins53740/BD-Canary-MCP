#!/usr/bin/env python3
"""
Ad-hoc harness for inspecting browseTags requests issued by the search_tags MCP tool.

Usage examples:
    uv run scripts/debug_search_tags.py "Kiln_Shell Temp_Average_Section_20 431"
    uv run scripts/debug_search_tags.py "Kiln_Shell Temp*" --search-path Secil.Portugal --no-cache
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Optional

import httpx

# Ensure repository src/ is on the import path
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from canary_mcp.server import search_tags  # type: ignore  # noqa: E402


def _install_httpx_probe() -> None:
    """
    Monkey-patch httpx.AsyncClient.post so we can log outgoing browseTags requests.

    The wrapper prints the request URL, JSON payload, status code, and the parsed JSON response
    body (truncated to avoid overly large dumps).
    """
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


async def _run(
    search_pattern: str,
    search_path: Optional[str],
    bypass_cache: bool,
) -> None:
    """
    Execute the search_tags MCP tool and display the resulting structure.
    """
    _install_httpx_probe()

    result = await search_tags.fn(
        search_pattern,
        bypass_cache=bypass_cache,
        search_path=search_path,
    )

    print("─" * 80)
    print("search_tags result:")
    print(json.dumps(result, indent=2, ensure_ascii=False))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Debug the search_tags MCP tool.")
    parser.add_argument(
        "search_pattern",
        help="Search string passed to the Canary browseTags API.",
    )
    parser.add_argument(
        "--search-path",
        dest="search_path",
        default=None,
        help="Optional namespace path to scope the search (empty string for global search).",
    )
    parser.add_argument(
        "--no-cache",
        dest="bypass_cache",
        action="store_true",
        help="Bypass in-memory cache and force a fresh Canary request.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        asyncio.run(
            _run(
                search_pattern=args.search_pattern,
                search_path=args.search_path,
                bypass_cache=args.bypass_cache,
            )
        )
    except KeyboardInterrupt:
        print("\nInterrupted by user.")


if __name__ == "__main__":
    main()
