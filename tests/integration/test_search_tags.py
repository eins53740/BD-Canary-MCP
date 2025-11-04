"""Integration tests for search_tags MCP tool."""

import os
from unittest.mock import MagicMock, patch

import httpx
import pytest

from canary_mcp.server import search_tags


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_tags_success():
    """Test successful tag search with results."""
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

        # Mock tag search API response
        mock_search_response = MagicMock()
        mock_search_response.json.return_value = {
            "tags": [
                {
                    "name": "Temperature",
                    "path": "Plant.Area1.Temperature",
                    "dataType": "float",
                    "description": "Kiln temperature sensor",
                },
                {
                    "name": "Temperature2",
                    "path": "Plant.Area2.Temperature",
                    "dataType": "float",
                    "description": "Secondary temperature sensor",
                },
            ]
        }
        mock_search_response.raise_for_status = MagicMock()
        mock_search_response.status_code = 200

        with patch("httpx.AsyncClient.post") as mock_post:
            # First call is auth, second is tag search
            mock_post.side_effect = [mock_auth_response, mock_search_response]

            result = await search_tags.fn("Temperature", bypass_cache=True)

            assert result["success"] is True
            assert result["count"] == 2
            assert len(result["tags"]) == 2
            assert result["pattern"] == "Temperature"
            assert result["tags"][0]["name"] == "Temperature"
            assert result["tags"][0]["path"] == "Plant.Area1.Temperature"
            assert result["tags"][0]["dataType"] == "float"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_tags_no_results():
    """Test tag search with no matching results."""
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

        # Empty tags response
        mock_search_response = MagicMock()
        mock_search_response.json.return_value = {"tags": []}
        mock_search_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = [mock_auth_response, mock_search_response]

            result = await search_tags.fn("NonExistentTag", bypass_cache=True)

            assert result["success"] is True
            assert result["count"] == 0
            assert result["tags"] == []
            assert result["pattern"] == "NonExistentTag"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_tags_empty_pattern():
    """Test tag search with empty search pattern."""
    result = await search_tags.fn("")

    assert result["success"] is False
    assert "error" in result
    assert "empty" in result["error"].lower()
    assert result["tags"] == []
    assert result["count"] == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_tags_whitespace_pattern():
    """Test tag search with whitespace-only pattern."""
    result = await search_tags.fn("   ")

    assert result["success"] is False
    assert "error" in result
    assert "empty" in result["error"].lower()
    assert result["tags"] == []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_tags_authentication_failure():
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

            result = await search_tags.fn("Temperature", bypass_cache=True)

            assert result["success"] is False
            assert "error" in result
            assert "Authentication failed" in result["error"]
            assert result["tags"] == []
            assert result["pattern"] == "Temperature"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_tags_api_error():
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
        mock_error_response.status_code = 500
        mock_error_response.text = "Internal Server Error"

        with patch("httpx.AsyncClient.post") as mock_post:
            # First call succeeds (auth), second fails (API error)
            mock_post.side_effect = [
                mock_auth_response,
                httpx.HTTPStatusError(
                    "500 Internal Server Error",
                    request=MagicMock(),
                    response=mock_error_response,
                ),
            ]

            result = await search_tags.fn("Temperature", bypass_cache=True)

            assert result["success"] is False
            assert "error" in result
            assert "API request failed" in result["error"]
            assert "500" in result["error"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_tags_network_error():
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

            result = await search_tags.fn("Temperature", bypass_cache=True)

            assert result["success"] is False
            assert "error" in result
            assert (
                "Network error" in result["error"]
                or "Authentication failed" in result["error"]
            )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_tags_missing_config():
    """Test handling of missing configuration."""
    with patch.dict(os.environ, {}, clear=True):
        result = await search_tags.fn("Temperature", bypass_cache=True)

        assert result["success"] is False
        assert "error" in result
        assert result["tags"] == []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_tags_malformed_response():
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
        mock_search_response = MagicMock()
        mock_search_response.json.return_value = {"invalid_key": "invalid_data"}
        mock_search_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = [mock_auth_response, mock_search_response]

            result = await search_tags.fn("Temperature", bypass_cache=True)

            # Should succeed but return empty tags
            assert result["success"] is True
            assert result["count"] == 0
            assert result["tags"] == []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_tags_wildcard_pattern():
    """Test tag search with wildcard pattern."""
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

        mock_search_response = MagicMock()
        mock_search_response.json.return_value = {
            "tags": [
                {"name": "Tag1", "path": "Plant.Tag1"},
                {"name": "Tag2", "path": "Plant.Tag2"},
            ]
        }
        mock_search_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = [mock_auth_response, mock_search_response]

            result = await search_tags.fn("Tag*")

            assert result["success"] is True
            assert result["count"] == 2
            assert result["pattern"] == "Tag*"
