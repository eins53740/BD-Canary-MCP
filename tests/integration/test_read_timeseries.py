"""Integration tests for read_timeseries MCP tool."""

import os
from unittest.mock import MagicMock, patch

import httpx
import pytest

from canary_mcp.server import read_timeseries


@pytest.mark.integration
@pytest.mark.asyncio
async def test_read_timeseries_success():
    """Test successful timeseries data retrieval."""
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

        # Mock timeseries data API response
        mock_data_response = MagicMock()
        mock_data_response.json.return_value = {
            "data": [
                {
                    "timestamp": "2025-10-30T12:00:00Z",
                    "value": 25.5,
                    "quality": "Good",
                    "tagName": "Plant.Temperature",
                },
                {
                    "timestamp": "2025-10-30T13:00:00Z",
                    "value": 26.2,
                    "quality": "Good",
                    "tagName": "Plant.Temperature",
                },
            ]
        }
        mock_data_response.raise_for_status = MagicMock()
        mock_data_response.status_code = 200

        with patch("httpx.AsyncClient.post") as mock_post:
            # First call is auth, second is data request
            mock_post.side_effect = [mock_auth_response, mock_data_response]

            result = await read_timeseries.fn(
                "Plant.Temperature", "2025-10-30T00:00:00Z", "2025-10-31T00:00:00Z"
            )

            assert result["success"] is True
            assert result["count"] == 2
            assert len(result["data"]) == 2
            assert result["data"][0]["timestamp"] == "2025-10-30T12:00:00Z"
            assert result["data"][0]["value"] == 25.5
            assert result["data"][0]["quality"] == "Good"
            assert result["tag_names"] == ["Plant.Temperature"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_read_timeseries_natural_language_time():
    """Test timeseries retrieval with natural language time expressions."""
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

        mock_data_response = MagicMock()
        mock_data_response.json.return_value = {"data": []}
        mock_data_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = [mock_auth_response, mock_data_response]

            result = await read_timeseries.fn("Plant.Tag", "yesterday", "now")

            assert result["success"] is True
            assert "start_time" in result
            assert "end_time" in result
            assert result["start_time"].endswith("Z")
            assert result["end_time"].endswith("Z")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_read_timeseries_multiple_tags():
    """Test timeseries retrieval for multiple tags."""
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

        mock_data_response = MagicMock()
        mock_data_response.json.return_value = {
            "data": [
                {
                    "timestamp": "2025-10-30T12:00:00Z",
                    "value": 25.5,
                    "quality": "Good",
                    "tagName": "Tag1",
                },
                {
                    "timestamp": "2025-10-30T12:00:00Z",
                    "value": 100.0,
                    "quality": "Good",
                    "tagName": "Tag2",
                },
            ]
        }
        mock_data_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post") as mock_post, \
             patch("canary_mcp.server.search_tags.fn") as mock_search:
            mock_post.side_effect = [mock_auth_response, mock_data_response]
            mock_search.return_value = {"success": True, "tags": [{"path": "Tag1"}, {"path": "Tag2"}]}

            result = await read_timeseries.fn(
                ["Tag1", "Tag2"], "2025-10-30T00:00:00Z", "2025-10-31T00:00:00Z"
            )

            assert result["success"] is True
            assert result["count"] == 2
            assert result["tag_names"] == ["Tag1", "Tag2"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_read_timeseries_empty_results():
    """Test timeseries retrieval with no data available."""
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

        mock_data_response = MagicMock()
        mock_data_response.json.return_value = {"data": []}
        mock_data_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = [mock_auth_response, mock_data_response]

            result = await read_timeseries.fn(
                "Plant.Tag", "2025-10-30T00:00:00Z", "2025-10-31T00:00:00Z"
            )

            assert result["success"] is True
            assert result["count"] == 0
            assert result["data"] == []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_read_timeseries_tag_not_found():
    """Test handling of non-existent tag."""
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

        with patch("httpx.AsyncClient.post") as mock_post, \
             patch("canary_mcp.server.search_tags.fn") as mock_search:
            mock_post.side_effect = [mock_auth_response, mock_data_response]
            mock_search.return_value = {"success": True, "tags": []}

            result = await read_timeseries.fn(
                "NonExistent", "2025-10-30T00:00:00Z", "2025-10-31T00:00:00Z"
            )

            assert result["success"] is False
            assert "error" in result
            assert "not found" in result["error"].lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_read_timeseries_empty_tag_name():
    """Test timeseries with empty tag name."""
    result = await read_timeseries.fn("", "2025-10-30T00:00:00Z", "2025-10-31T00:00:00Z")

    assert result["success"] is False
    assert "error" in result
    assert "empty" in result["error"].lower()
    assert result["data"] == []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_read_timeseries_invalid_time_expression():
    """Test timeseries with invalid time expression."""
    result = await read_timeseries.fn(
        "Plant.Tag", "invalid_time", "2025-10-31T00:00:00Z"
    )

    assert result["success"] is False
    assert "error" in result
    assert "time expression" in result["error"].lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_read_timeseries_start_after_end():
    """Test timeseries with start time after end time."""
    result = await read_timeseries.fn(
        "Plant.Tag", "2025-10-31T00:00:00Z", "2025-10-30T00:00:00Z"
    )

    assert result["success"] is False
    assert "error" in result
    assert "before" in result["error"].lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_read_timeseries_authentication_failure():
    """Test handling of authentication failure."""
    with patch.dict(
        os.environ,
        {
            "CANARY_SAF_BASE_URL": "https://test.canary.com/api/v1",
            "CANARY_VIEWS_BASE_URL": "https://test.canary.com",
            "CANARY_API_TOKEN": "invalid-token",
        },
    ):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = httpx.HTTPStatusError(
                "401 Unauthorized",
                request=MagicMock(),
                response=mock_response,
            )

            result = await read_timeseries.fn(
                "Plant.Tag", "2025-10-30T00:00:00Z", "2025-10-31T00:00:00Z"
            )

            assert result["success"] is False
            assert "error" in result
            assert "Authentication failed" in result["error"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_read_timeseries_api_error():
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

        mock_error_response = MagicMock()
        mock_error_response.status_code = 500
        mock_error_response.text = "Internal Server Error"

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = [
                mock_auth_response,
                httpx.HTTPStatusError(
                    "500 Internal Server Error",
                    request=MagicMock(),
                    response=mock_error_response,
                ),
            ]

            result = await read_timeseries.fn(
                "Plant.Tag", "2025-10-30T00:00:00Z", "2025-10-31T00:00:00Z"
            )

            assert result["success"] is False
            assert "error" in result
            assert "API request failed" in result["error"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_read_timeseries_network_error():
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
            mock_post.side_effect = httpx.ConnectError("Connection refused")

            result = await read_timeseries.fn(
                "Plant.Tag", "2025-10-30T00:00:00Z", "2025-10-31T00:00:00Z"
            )

            assert result["success"] is False
            assert "error" in result
            assert (
                "Network error" in result["error"]
                or "Authentication failed" in result["error"]
            )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_read_timeseries_missing_config():
    """Test handling of missing configuration."""
    with patch.dict(os.environ, {}, clear=True):
        result = await read_timeseries.fn(
            "Plant.Tag", "2025-10-30T00:00:00Z", "2025-10-31T00:00:00Z"
        )

        assert result["success"] is False
        assert "error" in result


@pytest.mark.integration
@pytest.mark.asyncio
async def test_read_timeseries_with_page_size():
    """Test timeseries retrieval with custom page size."""
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

        mock_data_response = MagicMock()
        mock_data_response.json.return_value = {"data": []}
        mock_data_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = [mock_auth_response, mock_data_response]

            result = await read_timeseries.fn(
                "Plant.Tag", "2025-10-30T00:00:00Z", "2025-10-31T00:00:00Z", page_size=500
            )

            assert result["success"] is True
            # Verify the page_size was passed in the request
            call_args = mock_post.call_args_list[1]
            assert call_args[1]["json"]["pageSize"] == 500
