"""HTTP helper utilities for Canary MCP tools."""

from __future__ import annotations

from typing import Any, Mapping, Optional

# Canonical mapping between MCP tools and HTTP methods.
# GET = idempotent lookups, POST = complex/batched requests requiring bodies.
TOOL_HTTP_METHODS: dict[str, str] = {
    "list_namespaces": "GET",
    "get_timezones": "GET",
    "get_available_aggregates": "GET",
    "search_tags": "POST",
    "get_tag_metadata": "POST",
    "get_tag_properties": "POST",
    "read_timeseries": "POST",
    "get_tag_data2": "POST",
    "get_asset_types": "POST",
    "get_asset_instances": "POST",
    "get_events_limit10": "POST",
    "read_compressed_timeseries": "POST",
    "read_summary_timeseries": "POST",
    "get_last_known_values": "POST",
    "get_tag_data_window": "POST",
    "browse_status": "GET",
}

__all__ = ["TOOL_HTTP_METHODS", "get_tool_http_method", "execute_tool_request"]


def get_tool_http_method(tool_name: str) -> str:
    """Return the configured HTTP method for a given tool."""
    try:
        return TOOL_HTTP_METHODS[tool_name]
    except KeyError as exc:  # pragma: no cover - defensive guard
        raise KeyError(
            f"Unknown tool '{tool_name}'. Update TOOL_HTTP_METHODS with the expected HTTP method."
        ) from exc


async def execute_tool_request(
    tool_name: str,
    client: Any,
    url: str,
    *,
    params: Optional[Mapping[str, Any]] = None,
    json: Any = None,
    method: Optional[str] = None,
) -> Any:
    """Execute an HTTP request for a tool, enforcing the canonical method."""
    resolved_method = (method or get_tool_http_method(tool_name)).upper()

    if resolved_method == "GET":
        if json is not None:
            raise ValueError(
                f"Tool '{tool_name}' requires GET requests; provide query parameters via 'params' "
                "instead of a JSON body."
            )
        return await client.get(url, params=params)

    if resolved_method == "POST":
        return await client.post(url, json=json, params=params)

    raise ValueError(
        f"HTTP method '{resolved_method}' is not supported for tool '{tool_name}'. "
        "Update execute_tool_request to handle this method explicitly."
    )
