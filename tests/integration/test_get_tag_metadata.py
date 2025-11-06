"""Integration tests for get_tag_metadata MCP tool."""

import os
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from canary_mcp.auth import CanaryAuthError
from canary_mcp.server import get_tag_metadata


def _configure_mock_async_client(
    mock_async_client: MagicMock,
    *,
    response: Optional[MagicMock] = None,
    post_side_effect: Optional[Exception] = None,
) -> MagicMock:
    """Prepare an async context manager-compatible httpx client mock."""

    http_client = MagicMock()
    http_client.post = AsyncMock()
    if post_side_effect is not None:
        http_client.post.side_effect = post_side_effect
    else:
        http_client.post.return_value = response
    http_client.aclose = AsyncMock()

    mock_async_client.return_value.__aenter__ = AsyncMock(return_value=http_client)
    mock_async_client.return_value.__aexit__ = AsyncMock(return_value=None)

    return http_client


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_tag_metadata_success():
    """Test successful tag metadata retrieval."""
    with patch.dict(
        os.environ,
        {
            "CANARY_SAF_BASE_URL": "https://test.canary.com/api/v1",
            "CANARY_VIEWS_BASE_URL": "https://test.canary.com",
            "CANARY_API_TOKEN": "test-token",
        },
    ):
        mock_properties_response = MagicMock()
        mock_properties_response.raise_for_status = MagicMock()
        mock_properties_response.json.return_value = {
            "properties": {
                "Plant.Area1.Temperature": {
                    "path": "Plant.Area1.Temperature",
                    "name": "Temperature",
                    "dataType": "float",
                    "description": "Kiln temperature sensor",
                    "units": "°C",
                    "minValue": 0,
                    "maxValue": 1500,
                }
            }
        }

        with patch("canary_mcp.server.search_tags.fn") as mock_search, patch(
            "canary_mcp.auth.CanaryAuthClient.get_valid_token"
        ) as mock_token, patch("httpx.AsyncClient", autospec=True) as mock_async_client:
            mock_search.return_value = {
                "success": True,
                "tags": [
                    {
                        "name": "Temperature",
                        "path": "Plant.Area1.Temperature",
                        "dataType": "float",
                        "description": "Kiln temperature sensor",
                        "units": "°C",
                        "minValue": 0,
                        "maxValue": 1500,
                        "updateRate": 1000,
                    }
                ],
            }
            mock_token.return_value = "session-123"
            _configure_mock_async_client(mock_async_client, response=mock_properties_response)

            result = await get_tag_metadata.fn("Plant.Area1.Temperature")

            assert result["success"] is True
            assert result["tag_path"] == "Plant.Area1.Temperature"
            assert result["metadata"]["name"] == "Temperature"
            assert result["metadata"]["path"] == "Plant.Area1.Temperature"
            assert result["metadata"]["dataType"] == "float"
            assert result["metadata"]["units"] == "°C"
            assert result["metadata"]["minValue"] == 0
            assert result["metadata"]["maxValue"] == 1500
            assert "properties" in result["metadata"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_tag_metadata_minimal_response():
    """Test metadata retrieval with minimal response fields."""
    with patch.dict(
        os.environ,
        {
            "CANARY_SAF_BASE_URL": "https://test.canary.com/api/v1",
            "CANARY_VIEWS_BASE_URL": "https://test.canary.com",
            "CANARY_API_TOKEN": "test-token",
        },
    ):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "properties": {
                "Plant.SimpleTag": {
                    "path": "Plant.SimpleTag",
                    "name": "SimpleTag",
                    "dataType": "int",
                    "description": "",
                    "units": "",
                }
            }
        }

        with patch("canary_mcp.server.search_tags.fn") as mock_search, patch(
            "canary_mcp.auth.CanaryAuthClient.get_valid_token"
        ) as mock_token, patch("httpx.AsyncClient", autospec=True) as mock_async_client:
            mock_search.return_value = {
                "success": True,
                "tags": [{"name": "SimpleTag", "path": "Plant.SimpleTag", "dataType": "int"}],
            }
            mock_token.return_value = "session-123"
            _configure_mock_async_client(mock_async_client, response=mock_response)

            result = await get_tag_metadata.fn("Plant.SimpleTag")

            assert result["success"] is True
            assert result["metadata"]["name"] == "SimpleTag"
            assert result["metadata"]["dataType"] == "int"
            assert result["metadata"]["description"] == ""
            assert result["metadata"]["units"] == ""


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_tag_metadata_empty_tag_path():
    """Test tag metadata with empty tag path."""
    result = await get_tag_metadata.fn("")

    assert result["success"] is False
    assert "error" in result
    assert "empty" in result["error"].lower()
    assert result["metadata"] == {}
    assert result["tag_path"] == ""


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_tag_metadata_whitespace_tag_path():
    """Test tag metadata with whitespace-only tag path."""
    result = await get_tag_metadata.fn("   ")

    assert result["success"] is False
    assert "error" in result
    assert "empty" in result["error"].lower()
    assert result["metadata"] == {}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_tag_metadata_authentication_failure():
    """Test handling of authentication failure."""
    with patch.dict(
        os.environ,
        {
            "CANARY_SAF_BASE_URL": "https://test.canary.com/api/v1",
            "CANARY_VIEWS_BASE_URL": "https://test.canary.com",
            "CANARY_API_TOKEN": "invalid-token",
        },
    ):
        with patch("canary_mcp.server.search_tags.fn") as mock_search, patch(
            "canary_mcp.auth.CanaryAuthClient.get_valid_token"
        ) as mock_token, patch("httpx.AsyncClient", autospec=True) as mock_async_client:
            mock_search.return_value = {
                "success": True,
                "tags": [{"path": "Plant.Tag1", "name": "Tag1", "dataType": "float"}],
            }
            mock_token.side_effect = CanaryAuthError("Unauthorized")
            _configure_mock_async_client(mock_async_client)

            result = await get_tag_metadata.fn("Plant.Tag1")

            assert result["success"] is False
            assert "error" in result
            assert "Authentication failed" in result["error"]
            assert result["metadata"] == {}
            assert result["tag_path"] == "Plant.Tag1"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_tag_metadata_api_error():
    """Test handling of API error responses."""
    with patch.dict(
        os.environ,
        {
            "CANARY_SAF_BASE_URL": "https://test.canary.com/api/v1",
            "CANARY_VIEWS_BASE_URL": "https://test.canary.com",
            "CANARY_API_TOKEN": "test-token",
        },
    ):
        with patch("canary_mcp.server.search_tags.fn") as mock_search, patch(
            "canary_mcp.auth.CanaryAuthClient.get_valid_token"
        ) as mock_token, patch("httpx.AsyncClient", autospec=True) as mock_async_client:
            mock_search.return_value = {
                "success": True,
                "tags": [{"path": "Plant.NonExistent", "name": "NonExistent"}],
            }
            mock_token.return_value = "session-123"

            error_response = httpx.Response(404, text="Not Found")
            request = httpx.Request("POST", "https://test.canary.com/api/v2/getTagProperties")
            _configure_mock_async_client(
                mock_async_client,
                post_side_effect=httpx.HTTPStatusError(
                    "API error", request=request, response=error_response
                ),
            )

            result = await get_tag_metadata.fn("Plant.NonExistent")

            assert result["success"] is False
            assert "error" in result
            assert "API request failed" in result["error"]
            assert "404" in result["error"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_tag_metadata_network_error():
    """Test handling of network connectivity errors."""
    with patch.dict(
        os.environ,
        {
            "CANARY_SAF_BASE_URL": "https://test.canary.com/api/v1",
            "CANARY_VIEWS_BASE_URL": "https://test.canary.com",
            "CANARY_API_TOKEN": "test-token",
        },
    ):
        with patch(
            "canary_mcp.auth.CanaryAuthClient.get_valid_token"
        ) as mock_token:
            mock_token.side_effect = httpx.ConnectError("Connection refused")

            result = await get_tag_metadata.fn("Plant.Tag1")

            assert result["success"] is False
            assert "error" in result
            assert (
                "Network error" in result["error"]
                or "Authentication failed" in result["error"]
            )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_tag_metadata_missing_config():
    """Test handling of missing configuration."""
    with patch.dict(os.environ, {}, clear=True):
        result = await get_tag_metadata.fn("Plant.Tag1")

        assert result["success"] is False
        assert "error" in result
        assert result["metadata"] == {}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_tag_metadata_malformed_response():
    """Test handling of malformed API response data."""
    with patch.dict(
        os.environ,
        {
            "CANARY_SAF_BASE_URL": "https://test.canary.com/api/v1",
            "CANARY_VIEWS_BASE_URL": "https://test.canary.com",
            "CANARY_API_TOKEN": "test-token",
        },
    ):
        with patch("canary_mcp.server.search_tags.fn") as mock_search, patch(
            "canary_mcp.auth.CanaryAuthClient.get_valid_token"
        ) as mock_token, patch("httpx.AsyncClient", autospec=True) as mock_async_client:
            mock_search.return_value = {"success": True, "tags": []}
            mock_token.return_value = "session-123"
            malformed_response = MagicMock()
            malformed_response.raise_for_status = MagicMock()
            malformed_response.json.return_value = {"invalid_key": "invalid_data"}

            _configure_mock_async_client(mock_async_client, response=malformed_response)

            result = await get_tag_metadata.fn("Plant.Tag1")

            assert result["success"] is False
            assert "not found" in result["error"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_tag_metadata_with_properties():
    """Test metadata retrieval with additional properties."""
    with patch.dict(
        os.environ,
        {
            "CANARY_SAF_BASE_URL": "https://test.canary.com/api/v1",
            "CANARY_VIEWS_BASE_URL": "https://test.canary.com",
            "CANARY_API_TOKEN": "test-token",
        },
    ):
        mock_properties_response = MagicMock()
        mock_properties_response.json.return_value = {
            "properties": {
                "Plant.Pressure": {
                    "path": "Plant.Pressure",
                    "name": "Pressure",
                    "dataType": "float",
                    "description": "",
                    "units": "kPa",
                    "alarmHigh": 100,
                    "alarmLow": 10,
                    "quality": "Good",
                }
            }
        }
        mock_properties_response.raise_for_status = MagicMock()

        with patch("canary_mcp.server.search_tags.fn") as mock_search, patch(
            "canary_mcp.auth.CanaryAuthClient.get_valid_token"
        ) as mock_token, patch("httpx.AsyncClient", autospec=True) as mock_async_client:
            mock_search.return_value = {
                "success": True,
                "tags": [
                    {
                        "name": "Pressure",
                        "path": "Plant.Pressure",
                        "dataType": "float",
                    }
                ],
            }
            mock_token.return_value = "session-123"
            _configure_mock_async_client(mock_async_client, response=mock_properties_response)

            result = await get_tag_metadata.fn("Plant.Pressure")

            assert result["success"] is True
            assert "properties" in result["metadata"]
            assert result["metadata"]["properties"]["alarmHigh"] == 100
            assert result["metadata"]["properties"]["alarmLow"] == 10
            assert result["metadata"]["properties"]["quality"] == "Good"
