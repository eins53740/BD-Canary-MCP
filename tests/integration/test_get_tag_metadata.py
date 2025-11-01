"""Integration tests for get_tag_metadata MCP tool."""

import os
from unittest.mock import MagicMock, patch

import httpx
import pytest

from canary_mcp.server import get_tag_metadata


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
        # Mock authentication client
        mock_auth_response = MagicMock()
        mock_auth_response.json.return_value = {"sessionToken": "session-123"}
        mock_auth_response.raise_for_status = MagicMock()

        # Mock tag metadata API response
        mock_metadata_response = MagicMock()
        mock_metadata_response.json.return_value = {
            "name": "Temperature",
            "path": "Plant.Area1.Temperature",
            "dataType": "float",
            "description": "Kiln temperature sensor",
            "units": "°C",
            "minValue": 0,
            "maxValue": 1500,
            "updateRate": 1000,
            "properties": {
                "quality": "Good",
                "timestamp": "2025-10-31T12:00:00Z",
            },
        }
        mock_metadata_response.raise_for_status = MagicMock()
        mock_metadata_response.status_code = 200

        with patch("httpx.AsyncClient.post") as mock_post:
            # First call is auth, second is metadata request
            mock_post.side_effect = [mock_auth_response, mock_metadata_response]

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
        mock_auth_response = MagicMock()
        mock_auth_response.json.return_value = {"sessionToken": "session-123"}
        mock_auth_response.raise_for_status = MagicMock()

        # Minimal metadata response
        mock_metadata_response = MagicMock()
        mock_metadata_response.json.return_value = {
            "tagName": "SimpleTag",
            "type": "int",
        }
        mock_metadata_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = [mock_auth_response, mock_metadata_response]

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
        # Mock authentication failure
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = httpx.HTTPStatusError(
                "401 Unauthorized",
                request=MagicMock(),
                response=mock_response,
            )

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
        mock_auth_response = MagicMock()
        mock_auth_response.json.return_value = {"sessionToken": "session-123"}
        mock_auth_response.raise_for_status = MagicMock()

        # Mock API error
        mock_error_response = MagicMock()
        mock_error_response.status_code = 404
        mock_error_response.text = "Tag not found"

        with patch("httpx.AsyncClient.post") as mock_post:
            # First call succeeds (auth), second fails (API error)
            mock_post.side_effect = [
                mock_auth_response,
                httpx.HTTPStatusError(
                    "404 Not Found",
                    request=MagicMock(),
                    response=mock_error_response,
                ),
            ]

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
        with patch("httpx.AsyncClient.post") as mock_post:
            # Simulate network error
            mock_post.side_effect = httpx.ConnectError("Connection refused")

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
        mock_auth_response = MagicMock()
        mock_auth_response.json.return_value = {"sessionToken": "session-123"}
        mock_auth_response.raise_for_status = MagicMock()

        # Malformed response (wrong structure)
        mock_metadata_response = MagicMock()
        mock_metadata_response.json.return_value = {"invalid_key": "invalid_data"}
        mock_metadata_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = [mock_auth_response, mock_metadata_response]

            result = await get_tag_metadata.fn("Plant.Tag1")

            # Should succeed but return minimal metadata
            assert result["success"] is True
            assert result["metadata"]["name"] == ""
            assert result["metadata"]["dataType"] == "unknown"


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
        mock_auth_response = MagicMock()
        mock_auth_response.json.return_value = {"sessionToken": "session-123"}
        mock_auth_response.raise_for_status = MagicMock()

        mock_metadata_response = MagicMock()
        mock_metadata_response.json.return_value = {
            "name": "Pressure",
            "path": "Plant.Pressure",
            "dataType": "float",
            "properties": {
                "alarmHigh": 100,
                "alarmLow": 10,
                "quality": "Good",
            },
        }
        mock_metadata_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = [mock_auth_response, mock_metadata_response]

            result = await get_tag_metadata.fn("Plant.Pressure")

            assert result["success"] is True
            assert "properties" in result["metadata"]
            assert result["metadata"]["properties"]["alarmHigh"] == 100
            assert result["metadata"]["properties"]["alarmLow"] == 10
            assert result["metadata"]["properties"]["quality"] == "Good"
