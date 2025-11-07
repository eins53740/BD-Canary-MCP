#!/usr/bin/env python3
"""Smoke-test runner for Canary MCP tools."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Awaitable, Callable, Optional

# Ensure src/ is importable
REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from canary_mcp.server import (  # noqa: E402  pylint: disable=wrong-import-position
    get_asset_catalog,
    get_last_known_values,
    get_metrics_summary,
    get_server_info,
    get_tag_metadata,
    get_tag_path,
    get_tag_properties,
    list_namespaces,
    mcp,
    ping,
    read_timeseries,
    search_tags,
)


class Status:
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    SKIP = "SKIP"


@dataclass
class ToolResult:
    name: str
    status: str
    message: str


ToolHandler = Callable[[], Awaitable[ToolResult]]


def _config_missing(error: str) -> bool:
    needles = [
        "not configured",
        "missing credentials",
        "Authentication failed",
        "Network error accessing Canary API",
    ]
    return any(token.lower() in error.lower() for token in needles)


def _success_message(payload: dict | str | None) -> str:
    if isinstance(payload, dict):
        if "count" in payload:
            return f"Returned count={payload['count']}"
        if payload.get("success") is False:
            return f"Tool responded with success=False ({payload.get('error', 'no details')})"
    if isinstance(payload, str):
        return payload
    return "Tool executed"


async def _test_ping() -> ToolResult:
    try:
        result = ping.fn()
        return ToolResult("ping", Status.PASS, result)
    except Exception as exc:  # pragma: no cover - CLI defensive
        return ToolResult("ping", Status.FAIL, str(exc))


async def _test_get_asset_catalog() -> ToolResult:
    try:
        result = get_asset_catalog.fn(limit=5)
        msg = _success_message(result)
        return ToolResult("get_asset_catalog", Status.PASS, msg)
    except Exception as exc:
        return ToolResult("get_asset_catalog", Status.FAIL, str(exc))


async def _test_search_tags(pattern: str) -> ToolResult:
    try:
        result = await search_tags.fn(pattern)
        msg = f"Returned {result.get('count', 0)} tags"
        return ToolResult("search_tags", Status.PASS, msg)
    except Exception as exc:
        status = Status.WARN if _config_missing(str(exc)) else Status.FAIL
        return ToolResult("search_tags", status, str(exc))


async def _test_get_tag_path(description: str) -> ToolResult:
    try:
        result = await get_tag_path.fn(description)
        if result.get("success"):
            msg = f"Resolved {result.get('most_likely_path')} (confidence={result.get('confidence')})"
            return ToolResult("get_tag_path", Status.PASS, msg)
        clarifier = result.get("clarifying_question") or result.get("error", "Clarification needed")
        return ToolResult("get_tag_path", Status.WARN, clarifier)
    except Exception as exc:
        return ToolResult("get_tag_path", Status.FAIL, str(exc))


async def _test_get_tag_metadata(sample_tag: str) -> ToolResult:
    try:
        result = await get_tag_metadata.fn(sample_tag)
        msg = result.get("metadata", {}).get("units", "Executed")
        return ToolResult("get_tag_metadata", Status.PASS, f"Units={msg}")
    except Exception as exc:
        status = Status.WARN if _config_missing(str(exc)) else Status.FAIL
        return ToolResult("get_tag_metadata", status, str(exc))


async def _test_get_tag_properties(sample_tag: str) -> ToolResult:
    try:
        result = await get_tag_properties.fn([sample_tag])
        msg = f"{len(result.get('properties', {}))} property blocks"
        return ToolResult("get_tag_properties", Status.PASS, msg)
    except Exception as exc:
        status = Status.WARN if _config_missing(str(exc)) else Status.FAIL
        return ToolResult("get_tag_properties", status, str(exc))


async def _test_read_timeseries(sample_tag: str) -> ToolResult:
    try:
        end = datetime.now()
        start = end - timedelta(minutes=5)
        result = await read_timeseries.fn(
            tag_names=[sample_tag],
            start_time=start.isoformat(),
            end_time=end.isoformat(),
        )
        msg = f"Returned {result.get('count', 0)} samples"
        return ToolResult("read_timeseries", Status.PASS, msg)
    except Exception as exc:
        status = Status.WARN if _config_missing(str(exc)) else Status.FAIL
        return ToolResult("read_timeseries", status, str(exc))


async def _test_get_last_known_values(sample_tag: str) -> ToolResult:
    try:
        result = await get_last_known_values.fn([sample_tag])
        msg = f"Returned {result.get('count', 0)} latest points"
        return ToolResult("get_last_known_values", Status.PASS, msg)
    except Exception as exc:
        status = Status.WARN if _config_missing(str(exc)) else Status.FAIL
        return ToolResult("get_last_known_values", status, str(exc))


async def _test_list_namespaces() -> ToolResult:
    try:
        result = await list_namespaces.fn()
        msg = f"{result.get('count', 0)} namespaces"
        return ToolResult("list_namespaces", Status.PASS, msg)
    except Exception as exc:
        status = Status.WARN if _config_missing(str(exc)) else Status.FAIL
        return ToolResult("list_namespaces", status, str(exc))


async def _test_get_server_info() -> ToolResult:
    try:
        result = await get_server_info.fn()
        if not result.get("success"):
            raise RuntimeError(result.get("error", "Unknown error"))
        msg = result.get("server_info", {}).get("canary_version", "Canary version unknown")
        return ToolResult("get_server_info", Status.PASS, msg)
    except Exception as exc:
        status = Status.WARN if _config_missing(str(exc)) else Status.FAIL
        return ToolResult("get_server_info", status, str(exc))


async def _test_get_metrics_summary() -> ToolResult:
    try:
        result = get_metrics_summary.fn()
        msg = f"Tracked {result.get('metrics', {}).get('total_requests', 0)} requests"
        return ToolResult("get_metrics_summary", Status.PASS, msg)
    except Exception as exc:
        return ToolResult("get_metrics_summary", Status.FAIL, str(exc))


async def run_suite(sample_tag: str, search_pattern: str, tag_description: str) -> list[ToolResult]:
    tests: list[ToolHandler] = [
        _test_ping,
        _test_get_asset_catalog,
        lambda: _test_search_tags(search_pattern),
        lambda: _test_get_tag_path(tag_description),
        lambda: _test_get_tag_metadata(sample_tag),
        lambda: _test_get_tag_properties(sample_tag),
        lambda: _test_read_timeseries(sample_tag),
        lambda: _test_get_last_known_values(sample_tag),
        _test_list_namespaces,
        _test_get_server_info,
        _test_get_metrics_summary,
    ]
    results: list[ToolResult] = []
    for handler in tests:
        results.append(await handler())
    return results


def _print_summary(results: list[ToolResult]) -> int:
    print("\n" + "=" * 72)
    print("MCP Tool Validation Summary")
    print("=" * 72)
    status_counts = {Status.PASS: 0, Status.WARN: 0, Status.FAIL: 0, Status.SKIP: 0}
    for result in results:
        status_counts[result.status] = status_counts.get(result.status, 0) + 1
        print(f"[{result.status}] {result.name:25s} {result.message}")
    print("-" * 72)
    print(
        f"PASS: {status_counts[Status.PASS]}  WARN: {status_counts[Status.WARN]}  "
        f"FAIL: {status_counts[Status.FAIL]}"
    )
    return 1 if status_counts[Status.FAIL] else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Canary MCP tools.")
    parser.add_argument(
        "--sample-tag",
        default=os.getenv("MCP_SAMPLE_TAG", "Maceira.Cement.Kiln6.Temperature.Outlet"),
        help="Tag used for metadata/read tests (default: %(default)s)",
    )
    parser.add_argument(
        "--search-pattern",
        default=os.getenv("MCP_SAMPLE_PATTERN", "Kiln*Temp"),
        help="Pattern passed to search_tags (default: %(default)s)",
    )
    parser.add_argument(
        "--tag-description",
        default=os.getenv("MCP_SAMPLE_DESCRIPTION", "kiln 6 shell temperature section 15"),
        help="Description passed to get_tag_path (default: %(default)s)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    results = asyncio.run(run_suite(args.sample_tag, args.search_pattern, args.tag_description))
    return _print_summary(results)


if __name__ == "__main__":
    raise SystemExit(main())
