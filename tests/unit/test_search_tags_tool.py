"""Unit tests for search_tags MCP tool (refactored)."""

from __future__ import annotations

from typing import Iterable
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from canary_mcp.server import search_tags

# ------------------------------
# Helpers & Fixtures
# ------------------------------


def _mk_response(json_payload: dict | list) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = json_payload
    resp.raise_for_status = MagicMock()
    return resp


def _mk_post_side_effect(payloads: Iterable[dict | list]) -> list[MagicMock]:
    """Create a list of MagicMocks to use as AsyncClient.post side effects,
    one per HTTP call in sequence."""
    return [_mk_response(p) for p in payloads]


@pytest.fixture
def env_with_root(monkeypatch):
    monkeypatch.setenv("CANARY_SAF_BASE_URL", "https://test.canary.com/api/v1")
    monkeypatch.setenv("CANARY_VIEWS_BASE_URL", "https://test.canary.com")
    monkeypatch.setenv("CANARY_API_TOKEN", "test-token")
    monkeypatch.setenv("CANARY_TAG_SEARCH_ROOT", "Secil.Portugal")
    return "Secil.Portugal"


@pytest.fixture
def env_without_root(monkeypatch):
    """Clear explicit root to exercise fallback behaviour in the tool."""
    monkeypatch.setenv("CANARY_SAF_BASE_URL", "https://test.canary.com/api/v1")
    monkeypatch.setenv("CANARY_VIEWS_BASE_URL", "https://test.canary.com")
    monkeypatch.setenv("CANARY_API_TOKEN", "test-token")
    # Intentionally DO NOT set CANARY_TAG_SEARCH_ROOT
    return "Secil.Portugal"  # expected fallback used by the tool


@pytest.fixture
def auth_ok():
    return {"sessionToken": "session-123"}


# ------------------------------
# Basic registration/doc tests
# ------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_tags_tool_registration():
    assert hasattr(search_tags, "fn")
    assert callable(search_tags.fn)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_tags_tool_documentation():
    assert search_tags.fn.__doc__ is not None
    doc = search_tags.fn.__doc__.lower()
    assert "search" in doc
    assert "tag" in doc


# ------------------------------
# Validation
# ------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("pattern", ["", "   "])
async def test_search_tags_rejects_empty_or_whitespace(pattern):
    """Empty or whitespace-only pattern should be rejected with consistent shape."""
    result = await search_tags.fn(pattern)

    assert result["success"] is False
    assert "error" in result and isinstance(result["error"], str)
    assert "empty" in result["error"].lower()
    assert result["tags"] == []
    assert result["count"] == 0
    # The tool defaults its root to Secil.Portugal
    assert result["search_path"] == "Secil.Portugal"
    assert "hint" in result


# ------------------------------
# Data parsing
# ------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_tags_data_parsing_valid_response(env_with_root, auth_ok):
    """Parses full object entries from API."""
    search_payload = {
        "tags": [
            {
                "name": "Temperature",
                "path": "Plant.Area1.Temperature",
                "dataType": "float",
                "description": "Temperature sensor",
            },
            {
                "name": "Pressure",
                "path": "Plant.Area1.Pressure",
                "dataType": "float",
                "description": "Pressure sensor",
            },
        ]
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = _mk_post_side_effect(
            [auth_ok, search_payload, {"tags": []}]
        )

        result = await search_tags.fn("Temp*")

    assert result["success"] is True
    assert result["count"] == 2
    assert len(result["tags"]) == 2
    assert result["tags"][0] == {
        "name": "Temperature",
        "path": "Plant.Area1.Temperature",
        "dataType": "float",
        "description": "Temperature sensor",
    }
    assert result["search_path"] == env_with_root
    assert "hint" in result


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_tags_parses_string_entries(env_with_root, auth_ok):
    """String-based entries should be normalised to objects with inferred fields."""
    search_payload = {
        "tags": [
            "Plant.Area1.Kiln.Kiln_Shell_Temp_Average_Section_20.Value",
            "Plant.Area1.Kiln.Kiln_Shell_Temp_Average_Section_200.Value",
        ]
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = _mk_post_side_effect(
            [auth_ok, search_payload, {"tags": []}]
        )

        result = await search_tags.fn("Kiln*")

    assert result["success"] is True
    assert result["count"] == 2
    assert len(result["tags"]) == 2

    first = result["tags"][0]
    assert first["path"] == "Plant.Area1.Kiln.Kiln_Shell_Temp_Average_Section_20.Value"
    assert first["name"] == "Value"  # name inferred from last path segment
    assert first["dataType"] == "unknown"  # default when not provided
    assert first["description"] == ""  # default when not provided


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_tags_data_parsing_missing_fields(env_with_root, auth_ok):
    """Objects with missing optional fields should get sensible defaults."""
    search_payload = {"tags": [{"name": "Tag1"}]}

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = _mk_post_side_effect(
            [auth_ok, search_payload, {"tags": []}]
        )

        result = await search_tags.fn("Tag1")

    assert result["success"] is True
    assert result["count"] == 1
    tag = result["tags"][0]
    assert tag["name"] == "Tag1"
    assert tag["path"] == "Tag1"  # fallback to name
    assert tag["dataType"] == "unknown"  # default
    assert tag["description"] == ""  # default
    assert result["search_path"] == env_with_root
    assert "hint" in result


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_tags_uses_configured_root_in_browse_call(env_with_root, auth_ok):
    """Ensure the request uses the configured search root (path) when browsing."""
    search_payload = {"tags": [{"name": "P431", "path": "Some.Path.P431.Value"}]}

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = _mk_post_side_effect(
            [auth_ok, search_payload, {"tags": []}]
        )

        result = await search_tags.fn("P431", bypass_cache=True)

        # At least 2 posts: auth and search (plus optional browse)
        assert len(mock_post.await_args_list) >= 2
        # The second call is the search request; verify the root path used
        browse_call = mock_post.await_args_list[1]
        assert browse_call.kwargs["json"]["path"] == env_with_root

    assert result["search_path"] == env_with_root
    assert "hint" in result


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_tags_falls_back_to_default_when_no_root(
    env_without_root, auth_ok
):
    """If no CANARY_TAG_SEARCH_ROOT is set, the tool should default to 'Secil.Portugal'."""
    search_payload = {
        "tags": [
            {
                "name": "P431",
                "path": (
                    "Secil.Portugal.Cement.Maceira.400 - Clinker Production."
                    "431 - Kiln.Normalised.Energy.P431.Value"
                ),
            }
        ]
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = _mk_post_side_effect(
            [auth_ok, search_payload, {"tags": []}]
        )

        result = await search_tags.fn("P431", bypass_cache=True)

        assert len(mock_post.await_args_list) >= 2
        browse_call = mock_post.await_args_list[1]
        assert browse_call.kwargs["json"]["path"] == env_without_root

    assert result["search_path"] == env_without_root
    assert result["count"] == 1
    assert result["tags"][0]["name"] == "P431"
    assert "hint" in result


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_tags_data_parsing_empty_tags(env_with_root, auth_ok):
    """Empty array is a valid success with zero results."""
    search_payload = {"tags": []}

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = _mk_post_side_effect(
            [auth_ok, search_payload, {"tags": []}]
        )

        result = await search_tags.fn("NonExistent", bypass_cache=True)

    assert result["success"] is True
    assert result["count"] == 0
    assert result["tags"] == []
    assert result["search_path"] == env_with_root
    assert "hint" in result


# ------------------------------
# Response shape (success & error)
# ------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_tags_response_format_success(env_with_root, auth_ok):
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = _mk_post_side_effect(
            [auth_ok, {"tags": []}, {"tags": []}]
        )

        result = await search_tags.fn("Pattern", bypass_cache=True)

    # Verify response structure
    assert set(result.keys()).issuperset(
        {"success", "tags", "count", "pattern", "search_path", "hint"}
    )
    assert result["success"] is True
    assert isinstance(result["tags"], list)
    assert isinstance(result["count"], int)
    assert result["pattern"] == "Pattern"
    assert result["search_path"] == env_with_root


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_tags_response_format_error():
    result = await search_tags.fn("")

    # Verify error response structure
    assert set(result.keys()).issuperset(
        {"success", "error", "tags", "count", "search_path", "hint"}
    )
    assert result["success"] is False
    assert isinstance(result["error"], str)
    assert result["tags"] == []
    assert result["count"] == 0
    assert result["search_path"] == "Secil.Portugal"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_tags_error_message_formatting():
    # Empty pattern
    r1 = await search_tags.fn("")
    assert "empty" in r1["error"].lower()
    assert r1["search_path"] == "Secil.Portugal"
    assert "hint" in r1

    # Whitespace pattern
    r2 = await search_tags.fn("   ")
    assert "empty" in r2["error"].lower()
    assert r2["search_path"] == "Secil.Portugal"
    assert "hint" in r2
