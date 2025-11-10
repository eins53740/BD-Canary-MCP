"""Unit tests for get_tag_properties MCP tool."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from canary_mcp.server import get_tag_properties


def _patched_env():
    return patch.dict(
        "os.environ",
        {
            "CANARY_SAF_BASE_URL": "https://test.canary.com/api/v1",
            "CANARY_VIEWS_BASE_URL": "https://test.canary.com",
            "CANARY_API_TOKEN": "test-token",
        },
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_tag_properties_validates_input():
    """The tool should fail when provided empty tag paths."""
    result_empty = await get_tag_properties.fn([])
    assert result_empty["success"] is False
    assert "required" in result_empty["error"].lower()

    result_blank = await get_tag_properties.fn(["   ", ""])
    assert result_blank["success"] is False
    assert "non-empty" in result_blank["error"].lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_tag_properties_success(monkeypatch):
    """Successful call returns properties mapped by tag path."""
    with _patched_env():
        post_mock = AsyncMock()
        post_mock.side_effect = [
            MagicMock(
                json=MagicMock(return_value={"sessionToken": "session-123"}),
                raise_for_status=MagicMock(),
            ),
            MagicMock(
                json=MagicMock(
                    return_value={
                        "properties": {
                            "Resolved.Tag.A": {"Description": "Example A"},
                            "Resolved.Tag.B": {"Description": "Example B"},
                        }
                    }
                ),
                raise_for_status=MagicMock(),
            ),
        ]

        search_mock = AsyncMock(
            side_effect=[
                {"success": True, "tags": [{"path": "Resolved.Tag.A"}]},
                {"success": True, "tags": [{"path": "Resolved.Tag.B"}]},
            ]
        )

        monkeypatch.setattr("httpx.AsyncClient.post", post_mock)
        monkeypatch.setattr(
            "canary_mcp.server.search_tags", SimpleNamespace(fn=search_mock)
        )

        result = await get_tag_properties.fn(["Tag.A", "Tag.B", "Tag.A"])

        assert result["success"] is True
        assert result["count"] == 2
        assert result["properties"]["Resolved.Tag.A"]["Description"] == "Example A"
        assert result["resolved_paths"]["Tag.A"] == "Resolved.Tag.A"
        assert result["resolved_paths"]["Tag.B"] == "Resolved.Tag.B"
        assert result["requested"] == ["Tag.A", "Tag.B"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_tag_properties_propagates_errors(monkeypatch):
    """HTTP errors should be surfaced with context."""
    with _patched_env():
        http_error = httpx.HTTPStatusError(
            "boom",
            request=MagicMock(),
            response=MagicMock(status_code=500, text="Internal error"),
        )

        post_mock = AsyncMock()
        post_mock.side_effect = [
            MagicMock(
                json=MagicMock(return_value={"sessionToken": "session-123"}),
                raise_for_status=MagicMock(),
            ),
            MagicMock(
                json=MagicMock(side_effect=http_error),
                raise_for_status=MagicMock(side_effect=http_error),
                response=MagicMock(status_code=500, text="Internal error"),
            ),
        ]

        search_mock = AsyncMock(
            return_value={"success": True, "tags": [{"path": "Resolved.Tag.A"}]}
        )

        monkeypatch.setattr("httpx.AsyncClient.post", post_mock)
        monkeypatch.setattr(
            "canary_mcp.server.search_tags", SimpleNamespace(fn=search_mock)
        )

        result = await get_tag_properties.fn(["Tag.A"])

        assert result["success"] is False
        assert "error" in result
        assert result["properties"] == {}
