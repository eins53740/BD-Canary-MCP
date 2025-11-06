"""Integration tests for get_server_info MCP tool."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from canary_mcp.auth import CanaryAuthClient
from canary_mcp.server import get_server_info


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_server_info_success():
    """Test successful server info retrieval with all data."""
    with patch.dict(
        os.environ,
        {
            "CANARY_SAF_BASE_URL": "https://test.canary.local:55236/api/v2",
            "CANARY_VIEWS_BASE_URL": "https://test.canary.local:55236",
            "CANARY_API_TOKEN": "test-token-123",
        },
    ):
        # Mock authentication
        mock_auth_client = AsyncMock(spec=CanaryAuthClient)
        mock_auth_client.get_valid_token = AsyncMock(return_value="valid-token-123")
        mock_auth_client.__aenter__ = AsyncMock(return_value=mock_auth_client)
        mock_auth_client.__aexit__ = AsyncMock(return_value=None)

        # Mock HTTP responses
        mock_timezones_response = MagicMock()
        mock_timezones_response.status_code = 200
        mock_timezones_response.json.return_value = {
            "statusCode": "Good",
            "timeZones": ["UTC", "America/New_York", "Europe/London", "Asia/Tokyo"],
        }

        mock_aggregates_response = MagicMock()
        mock_aggregates_response.status_code = 200
        mock_aggregates_response.json.return_value = {
            "statusCode": "Good",
            "aggregates": ["TimeAverage2", "TimeSum", "Min", "Max", "Count"],
        }

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(
            side_effect=[mock_timezones_response, mock_aggregates_response]
        )
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=None)

        with patch("canary_mcp.server.CanaryAuthClient", return_value=mock_auth_client):
            with patch("canary_mcp.server.httpx.AsyncClient", return_value=mock_http_client):
                result = await get_server_info.fn()

        assert result["success"] is True
        assert "server_info" in result
        assert "mcp_info" in result
        assert result["server_info"]["connected"] is True
        assert result["server_info"]["api_version"] == "v2"
        assert len(result["server_info"]["supported_timezones"]) == 4
        assert len(result["server_info"]["supported_aggregates"]) == 5
        assert result["mcp_info"]["server_name"] == "Canary MCP Server"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_server_info_many_timezones():
    """Test server info with many timezones (should limit to 10 for readability)."""
    with patch.dict(
        os.environ,
        {
            "CANARY_SAF_BASE_URL": "https://test.canary.local:55236/api/v2",
            "CANARY_VIEWS_BASE_URL": "https://test.canary.local:55236",
            "CANARY_API_TOKEN": "test-token-123",
        },
    ):
        mock_auth_client = AsyncMock(spec=CanaryAuthClient)
        mock_auth_client.get_valid_token = AsyncMock(return_value="valid-token-123")
        mock_auth_client.__aenter__ = AsyncMock(return_value=mock_auth_client)
        mock_auth_client.__aexit__ = AsyncMock(return_value=None)

        # Create 50 timezones
        many_timezones = [f"Timezone_{i}" for i in range(50)]

        mock_timezones_response = MagicMock()
        mock_timezones_response.status_code = 200
        mock_timezones_response.json.return_value = {"timeZones": many_timezones}

        mock_aggregates_response = MagicMock()
        mock_aggregates_response.status_code = 200
        mock_aggregates_response.json.return_value = {"aggregates": ["TimeAverage2"]}

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(
            side_effect=[mock_timezones_response, mock_aggregates_response]
        )
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=None)

        with patch("canary_mcp.server.CanaryAuthClient", return_value=mock_auth_client):
            with patch("canary_mcp.server.httpx.AsyncClient", return_value=mock_http_client):
                result = await get_server_info.fn()

        assert result["success"] is True
        assert len(result["server_info"]["supported_timezones"]) == 10  # Limited to 10
        assert result["server_info"]["total_timezones"] == 50  # But shows total


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_server_info_list_response_format():
    """Test server info when API returns lists instead of dicts."""
    with patch.dict(
        os.environ,
        {
            "CANARY_SAF_BASE_URL": "https://test.canary.local:55236/api/v2",
            "CANARY_VIEWS_BASE_URL": "https://test.canary.local:55236",
            "CANARY_API_TOKEN": "test-token-123",
        },
    ):
        mock_auth_client = AsyncMock(spec=CanaryAuthClient)
        mock_auth_client.get_valid_token = AsyncMock(return_value="valid-token-123")
        mock_auth_client.__aenter__ = AsyncMock(return_value=mock_auth_client)
        mock_auth_client.__aexit__ = AsyncMock(return_value=None)

        # Mock responses as arrays (alternative format)
        mock_timezones_response = MagicMock()
        mock_timezones_response.status_code = 200
        mock_timezones_response.json.return_value = ["UTC", "PST", "EST"]

        mock_aggregates_response = MagicMock()
        mock_aggregates_response.status_code = 200
        mock_aggregates_response.json.return_value = ["Min", "Max", "Avg"]

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(
            side_effect=[mock_timezones_response, mock_aggregates_response]
        )
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=None)

        with patch("canary_mcp.server.CanaryAuthClient", return_value=mock_auth_client):
            with patch("canary_mcp.server.httpx.AsyncClient", return_value=mock_http_client):
                result = await get_server_info.fn()

        assert result["success"] is True
        assert len(result["server_info"]["supported_timezones"]) == 3
        assert len(result["server_info"]["supported_aggregates"]) == 3


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_server_info_auth_failure():
    """Test server info with authentication failure."""
    with patch.dict(
        os.environ,
        {
            "CANARY_SAF_BASE_URL": "https://test.canary.local:55236/api/v2",
            "CANARY_VIEWS_BASE_URL": "https://test.canary.local:55236",
            "CANARY_API_TOKEN": "invalid-token",
        },
    ):
        from canary_mcp.auth import CanaryAuthError

        mock_auth_client = AsyncMock(spec=CanaryAuthClient)
        mock_auth_client.get_valid_token = AsyncMock(
            side_effect=CanaryAuthError("Invalid API token")
        )
        mock_auth_client.__aenter__ = AsyncMock(return_value=mock_auth_client)
        mock_auth_client.__aexit__ = AsyncMock(return_value=None)

        with patch("canary_mcp.server.CanaryAuthClient", return_value=mock_auth_client):
            result = await get_server_info.fn()

        assert result["success"] is False
        assert "Authentication failed" in result["error"]
        assert result["server_info"] == {}
        assert result["mcp_info"] == {}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_server_info_api_error():
    """Test server info with API request failure."""
    with patch.dict(
        os.environ,
        {
            "CANARY_SAF_BASE_URL": "https://test.canary.local:55236/api/v2",
            "CANARY_VIEWS_BASE_URL": "https://test.canary.local:55236",
            "CANARY_API_TOKEN": "test-token-123",
        },
    ):
        mock_auth_client = AsyncMock(spec=CanaryAuthClient)
        mock_auth_client.get_valid_token = AsyncMock(return_value="valid-token-123")
        mock_auth_client.__aenter__ = AsyncMock(return_value=mock_auth_client)
        mock_auth_client.__aexit__ = AsyncMock(return_value=None)

        # Mock HTTP error response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Server error", request=MagicMock(), response=mock_response
            )
        )
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=None)

        with patch("canary_mcp.server.CanaryAuthClient", return_value=mock_auth_client):
            with patch("canary_mcp.server.httpx.AsyncClient", return_value=mock_http_client):
                result = await get_server_info.fn()

        assert result["success"] is False
        assert "API request failed with status 500" in result["error"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_server_info_network_error():
    """Test server info with network connection error."""
    with patch.dict(
        os.environ,
        {
            "CANARY_SAF_BASE_URL": "https://test.canary.local:55236/api/v2",
            "CANARY_VIEWS_BASE_URL": "https://test.canary.local:55236",
            "CANARY_API_TOKEN": "test-token-123",
        },
    ):
        mock_auth_client = AsyncMock(spec=CanaryAuthClient)
        mock_auth_client.get_valid_token = AsyncMock(return_value="valid-token-123")
        mock_auth_client.__aenter__ = AsyncMock(return_value=mock_auth_client)
        mock_auth_client.__aexit__ = AsyncMock(return_value=None)

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(
            side_effect=httpx.RequestError("Connection failed")
        )
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=None)

        with patch("canary_mcp.server.CanaryAuthClient", return_value=mock_auth_client):
            with patch("canary_mcp.server.httpx.AsyncClient", return_value=mock_http_client):
                result = await get_server_info.fn()

        assert result["success"] is False
        assert "Network error" in result["error"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_server_info_missing_config():
    """Test server info with missing CANARY_VIEWS_BASE_URL configuration."""
    with patch.dict(os.environ, {}, clear=True):
        result = await get_server_info.fn()

        assert result["success"] is False
        assert "CANARY_VIEWS_BASE_URL not configured" in result["error"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_server_info_empty_response():
    """Test server info with empty API responses."""
    with patch.dict(
        os.environ,
        {
            "CANARY_SAF_BASE_URL": "https://test.canary.local:55236/api/v2",
            "CANARY_VIEWS_BASE_URL": "https://test.canary.local:55236",
            "CANARY_API_TOKEN": "test-token-123",
        },
    ):
        mock_auth_client = AsyncMock(spec=CanaryAuthClient)
        mock_auth_client.get_valid_token = AsyncMock(return_value="valid-token-123")
        mock_auth_client.__aenter__ = AsyncMock(return_value=mock_auth_client)
        mock_auth_client.__aexit__ = AsyncMock(return_value=None)

        # Mock empty responses
        mock_timezones_response = MagicMock()
        mock_timezones_response.status_code = 200
        mock_timezones_response.json.return_value = {"timeZones": []}

        mock_aggregates_response = MagicMock()
        mock_aggregates_response.status_code = 200
        mock_aggregates_response.json.return_value = {"aggregates": []}

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(
            side_effect=[mock_timezones_response, mock_aggregates_response]
        )
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=None)

        with patch("canary_mcp.server.CanaryAuthClient", return_value=mock_auth_client):
            with patch("canary_mcp.server.httpx.AsyncClient", return_value=mock_http_client):
                result = await get_server_info.fn()

        assert result["success"] is True
        assert result["server_info"]["total_timezones"] == 0
        assert result["server_info"]["total_aggregates"] == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_server_info_malformed_response():
    """Test server info with malformed API response (unexpected error)."""
    with patch.dict(
        os.environ,
        {
            "CANARY_SAF_BASE_URL": "https://test.canary.local:55236/api/v2",
            "CANARY_VIEWS_BASE_URL": "https://test.canary.local:55236",
            "CANARY_API_TOKEN": "test-token-123",
        },
    ):
        mock_auth_client = AsyncMock(spec=CanaryAuthClient)
        mock_auth_client.get_valid_token = AsyncMock(return_value="valid-token-123")
        mock_auth_client.__aenter__ = AsyncMock(return_value=mock_auth_client)
        mock_auth_client.__aexit__ = AsyncMock(return_value=None)

        # Mock response with invalid JSON that raises exception
        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(side_effect=ValueError("Invalid JSON"))
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=None)

        with patch("canary_mcp.server.CanaryAuthClient", return_value=mock_auth_client):
            with patch("canary_mcp.server.httpx.AsyncClient", return_value=mock_http_client):
                result = await get_server_info.fn()

        assert result["success"] is False
        assert "Unexpected error" in result["error"]
