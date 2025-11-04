"""Unit tests for get_tag_metadata MCP tool."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from canary_mcp.server import get_tag_metadata


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
async def test_get_tag_metadata_tool_registration():
    assert hasattr(get_tag_metadata, "fn")
    assert callable(get_tag_metadata.fn)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_tag_metadata_empty_tag_path_validation():
    result = await get_tag_metadata.fn("")
    assert result["success"] is False
    assert result["metadata"] == {}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_tag_metadata_data_parsing_valid_response(monkeypatch):
    mock_response_data = {
        "properties": {
            "Plant.Area1.Temperature": {
                "Description": "Temperature sensor",
                "Units": "°C",
                "DataType": "float",
                "engHigh": "1500",
                "engLow": "0",
                "updateRate": "1000",
            }
        }
    }

    with _patched_env():
        post_mock = AsyncMock()
        post_mock.side_effect = [
            MagicMock(
                json=MagicMock(return_value={"sessionToken": "session-123"}),
                raise_for_status=MagicMock(),
            ),
            MagicMock(
                json=MagicMock(return_value=mock_response_data),
                raise_for_status=MagicMock(),
            ),
        ]

        search_mock = AsyncMock(
            return_value={"success": True, "tags": [{"path": "Plant.Area1.Temperature"}]}
        )

        monkeypatch.setattr("httpx.AsyncClient.post", post_mock)
        monkeypatch.setattr("canary_mcp.server.search_tags", SimpleNamespace(fn=search_mock))

        result = await get_tag_metadata.fn("Plant.Area1.Temperature")

        assert result["success"] is True
        assert result["resolved_path"] == "Plant.Area1.Temperature"
        metadata = result["metadata"]
        assert metadata["name"] == "Temperature sensor"
        assert metadata["path"] == "Plant.Area1.Temperature"
        assert metadata["dataType"] == "float"
        assert metadata["units"] == "°C"
        assert metadata["engHigh"] == "1500"
        assert metadata["engLow"] == "0"
        assert "properties" in metadata


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_tag_metadata_resolves_short_identifier(monkeypatch):
    mock_response_data = {
        "properties": {
            "Resolved.Tag.Path": {
                "Description": "Example",
                "DataType": "int",
            }
        }
    }

    with _patched_env():
        post_mock = AsyncMock()
        post_mock.side_effect = [
            MagicMock(
                json=MagicMock(return_value={"sessionToken": "session-123"}),
                raise_for_status=MagicMock(),
            ),
            MagicMock(
                json=MagicMock(return_value=mock_response_data),
                raise_for_status=MagicMock(),
            ),
        ]

        search_mock = AsyncMock(
            return_value={"success": True, "tags": [{"path": "Resolved.Tag.Path"}]}
        )

        monkeypatch.setattr("httpx.AsyncClient.post", post_mock)
        monkeypatch.setattr("canary_mcp.server.search_tags", SimpleNamespace(fn=search_mock))

        result = await get_tag_metadata.fn("ShortTag")

        assert result["success"] is True
        assert result["resolved_path"] == "Resolved.Tag.Path"
        assert result["metadata"]["path"] == "Resolved.Tag.Path"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_tag_metadata_handles_http_error(monkeypatch):
    http_error = httpx.HTTPStatusError(
        "500",
        request=MagicMock(),
        response=MagicMock(status_code=500, text="Internal error"),
    )

    with _patched_env():
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
            return_value={"success": True, "tags": [{"path": "Plant.Area1.Temperature"}]}
        )

        monkeypatch.setattr("httpx.AsyncClient.post", post_mock)
        monkeypatch.setattr("canary_mcp.server.search_tags", SimpleNamespace(fn=search_mock))

        result = await get_tag_metadata.fn("Plant.Area1.Temperature")

        assert result["success"] is False
        assert "error" in result
