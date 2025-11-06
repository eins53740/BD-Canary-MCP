"""Integration tests for list_namespaces MCP tool."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from canary_mcp.server import list_namespaces


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_namespaces_success():
    """Test successful namespace retrieval."""
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

        # Mock namespace API response
        mock_ns_response = MagicMock()
        mock_ns_response.json.return_value = {
            "nodes": [
                {"path": "Plant.Area1", "id": "1"},
                {"path": "Plant.Area2", "id": "2"},
                {"path": "Plant.Area3", "id": "3"},
            ]
        }
        mock_ns_response.raise_for_status = MagicMock()
        mock_ns_response.status_code = 200

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, patch(
            "httpx.AsyncClient.get", new_callable=AsyncMock
        ) as mock_get:
            mock_post.side_effect = [mock_auth_response]
            mock_get.return_value = mock_ns_response

            result = await list_namespaces.fn()

            assert result["success"] is True
            assert result["count"] == 3
            assert len(result["namespaces"]) == 3
            assert "Plant.Area1" in result["namespaces"]
            assert "Plant.Area2" in result["namespaces"]
            assert "Plant.Area3" in result["namespaces"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_namespaces_empty_response():
    """Test handling of empty namespace list."""
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

        # Empty nodes response
        mock_ns_response = MagicMock()
        mock_ns_response.json.return_value = {"nodes": []}
        mock_ns_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, patch(
            "httpx.AsyncClient.get", new_callable=AsyncMock
        ) as mock_get:
            mock_post.side_effect = [mock_auth_response]
            mock_get.return_value = mock_ns_response

            result = await list_namespaces.fn()

            assert result["success"] is True
            assert result["count"] == 0
            assert result["namespaces"] == []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_namespaces_authentication_failure():
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

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.HTTPStatusError(
                "401 Unauthorized",
                request=MagicMock(),
                response=mock_response,
            )

            result = await list_namespaces.fn()

            assert result["success"] is False
            assert "error" in result
            assert "Authentication failed" in result["error"]
            assert result["namespaces"] == []
            assert result["count"] == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_namespaces_api_error():
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

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, patch(
            "httpx.AsyncClient.get", new_callable=AsyncMock
        ) as mock_get:
            mock_post.side_effect = [mock_auth_response]
            mock_get.side_effect = httpx.HTTPStatusError(
                "500 Internal Server Error",
                request=MagicMock(),
                response=mock_error_response,
            )

            result = await list_namespaces.fn()

            assert result["success"] is False
            assert "error" in result
            assert "API request failed" in result["error"]
            assert "500" in result["error"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_namespaces_network_error():
    """Test handling of network connectivity errors."""
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

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, patch(
            "httpx.AsyncClient.get", new_callable=AsyncMock
        ) as mock_get:
            mock_post.side_effect = [mock_auth_response]
            mock_get.side_effect = httpx.ConnectError("Connection refused")

            result = await list_namespaces.fn()

            assert result["success"] is False
            assert "error" in result
            assert "Network error" in result["error"] or "Authentication failed" in result["error"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_namespaces_missing_config():
    """Test handling of missing configuration."""
    with patch.dict(os.environ, {}, clear=True):
        result = await list_namespaces.fn()

        assert result["success"] is False
        assert "error" in result
        assert result["namespaces"] == []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_namespaces_malformed_response():
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
        mock_ns_response = MagicMock()
        mock_ns_response.json.return_value = {"invalid_key": "invalid_data"}
        mock_ns_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, patch(
            "httpx.AsyncClient.get", new_callable=AsyncMock
        ) as mock_get:
            mock_post.side_effect = [mock_auth_response]
            mock_get.return_value = mock_ns_response

            result = await list_namespaces.fn()

            # Should succeed but return empty namespaces
            assert result["success"] is True
            assert result["count"] == 0
            assert result["namespaces"] == []
