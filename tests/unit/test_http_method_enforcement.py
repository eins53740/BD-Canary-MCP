"""Unit tests for HTTP method enforcement helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from canary_mcp.http_client import (
    TOOL_HTTP_METHODS,
    execute_tool_request,
    get_tool_http_method,
)


@pytest.mark.unit
def test_tool_http_method_matrix_includes_expected_tools():
    """Ensure the canonical method map covers the core historian tools."""
    expected = {
        "list_namespaces": "GET",
        "search_tags": "POST",
        "get_tag_metadata": "POST",
        "get_tag_properties": "POST",
        "read_timeseries": "POST",
    }

    for tool_name, method in expected.items():
        assert TOOL_HTTP_METHODS[tool_name] == method
        assert get_tool_http_method(tool_name) == method


@pytest.mark.unit
def test_get_tool_http_method_unknown_tool():
    """Unknown tool names should surface an actionable error."""
    with pytest.raises(KeyError):
        get_tool_http_method("nonexistent_tool")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_tool_request_uses_get_for_idempotent_tools():
    """list_namespaces should perform GET requests with query parameters."""
    response = MagicMock()
    client = SimpleNamespace(
        get=AsyncMock(return_value=response),
        post=AsyncMock(),
    )

    result = await execute_tool_request(
        "list_namespaces",
        client,
        "https://example.test/api/v2/browseNodes",
        params={"apiToken": "token-123"},
    )

    assert result is response
    client.get.assert_awaited_once_with(
        "https://example.test/api/v2/browseNodes",
        params={"apiToken": "token-123"},
    )
    assert client.post.await_count == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_tool_request_uses_post_for_complex_tools():
    """search_tags should issue POST requests with a JSON payload."""
    response = MagicMock()
    client = SimpleNamespace(
        get=AsyncMock(),
        post=AsyncMock(return_value=response),
    )

    payload = {"apiToken": "token-123", "search": "Kiln*"}
    result = await execute_tool_request(
        "search_tags",
        client,
        "https://example.test/api/v2/browseTags",
        json=payload,
    )

    assert result is response
    client.post.assert_awaited_once_with(
        "https://example.test/api/v2/browseTags",
        json=payload,
        params=None,
    )
    assert client.get.await_count == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_tool_request_rejects_body_on_get():
    """Supplying a JSON body for GET-only tools raises ValueError."""
    client = SimpleNamespace(
        get=AsyncMock(),
        post=AsyncMock(),
    )

    with pytest.raises(ValueError) as exc:
        await execute_tool_request(
            "list_namespaces",
            client,
            "https://example.test/api/v2/browseNodes",
            json={"apiToken": "token-123"},
        )

    message = str(exc.value)
    assert "GET" in message
    assert "list_namespaces" in message
