"""Integration tests for Canary API authentication."""

import os
from unittest.mock import MagicMock, patch

import httpx
import pytest

from canary_mcp.auth import CanaryAuthClient, CanaryAuthError, validate_config


@pytest.mark.integration
@pytest.mark.asyncio
async def test_successful_authentication():
    """Test that authentication succeeds with valid credentials."""
    # Mock environment variables
    with patch.dict(
        os.environ,
        {
            "CANARY_SAF_BASE_URL": "https://test.canary.com/api/v1",
            "CANARY_VIEWS_BASE_URL": "https://test.canary.com",
            "CANARY_API_TOKEN": "test-token-123",
            "CANARY_SESSION_TIMEOUT_MS": "120000",
        },
    ):
        async with CanaryAuthClient() as client:
            # Mock the HTTP response
            mock_response = MagicMock()
            mock_response.json.return_value = {"sessionToken": "session-abc-123"}
            mock_response.raise_for_status = MagicMock()

            with patch.object(
                client._client, "post", return_value=mock_response  # type: ignore
            ):
                token = await client.authenticate()

                assert token == "session-abc-123"
                assert client._session_token == "session-abc-123"
                assert client._token_expires_at is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_token_refresh_functionality():
    """Test that token refresh works correctly."""
    with patch.dict(
        os.environ,
        {
            "CANARY_SAF_BASE_URL": "https://test.canary.com/api/v1",
            "CANARY_VIEWS_BASE_URL": "https://test.canary.com",
            "CANARY_API_TOKEN": "test-token-123",
            "CANARY_SESSION_TIMEOUT_MS": "120000",
        },
    ):
        async with CanaryAuthClient() as client:
            # Mock initial authentication
            mock_response1 = MagicMock()
            mock_response1.json.return_value = {"sessionToken": "session-old"}
            mock_response1.raise_for_status = MagicMock()

            # Mock token refresh
            mock_response2 = MagicMock()
            mock_response2.json.return_value = {"sessionToken": "session-new"}
            mock_response2.raise_for_status = MagicMock()

            with patch.object(
                client._client,  # type: ignore
                "post",
                side_effect=[mock_response1, mock_response2],
            ):
                # Initial authentication
                token1 = await client.authenticate()
                assert token1 == "session-old"

                # Refresh token
                token2 = await client.refresh_token()
                assert token2 == "session-new"
                assert token1 != token2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_authentication_with_invalid_token():
    """Test authentication failure with invalid API token."""
    with patch.dict(
        os.environ,
        {
            "CANARY_SAF_BASE_URL": "https://test.canary.com/api/v1",
            "CANARY_VIEWS_BASE_URL": "https://test.canary.com",
            "CANARY_API_TOKEN": "invalid-token",
        },
    ):
        async with CanaryAuthClient() as client:
            # Mock 401 unauthorized response
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"

            with patch.object(
                client._client,  # type: ignore
                "post",
                side_effect=httpx.HTTPStatusError(
                    "401 Unauthorized",
                    request=MagicMock(),
                    response=mock_response,
                ),
            ):
                with pytest.raises(CanaryAuthError) as exc_info:
                    await client.authenticate()

                assert "Invalid API token" in str(exc_info.value)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_authentication_with_missing_credentials():
    """Test authentication failure when credentials are missing."""
    with patch.dict(
        os.environ,
        {
            # Missing CANARY_API_TOKEN
            "CANARY_SAF_BASE_URL": "https://test.canary.com/api/v1",
            "CANARY_VIEWS_BASE_URL": "https://test.canary.com",
        },
        clear=True,
    ):
        async with CanaryAuthClient() as client:
            with pytest.raises(CanaryAuthError) as exc_info:
                await client.authenticate()

            assert "Missing required credentials" in str(exc_info.value)
            assert "CANARY_API_TOKEN" in str(exc_info.value)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_retry_logic_on_connection_failure():
    """Test that retry logic works with exponential backoff."""
    with patch.dict(
        os.environ,
        {
            "CANARY_SAF_BASE_URL": "https://test.canary.com/api/v1",
            "CANARY_VIEWS_BASE_URL": "https://test.canary.com",
            "CANARY_API_TOKEN": "test-token",
            "CANARY_RETRY_ATTEMPTS": "3",
        },
    ):
        async with CanaryAuthClient() as client:
            # Track call count
            call_count = 0

            async def mock_post_with_retries(*args, **kwargs):  # type: ignore
                nonlocal call_count
                call_count += 1

                # Fail first 2 attempts, succeed on 3rd
                if call_count <= 2:
                    raise httpx.ConnectError("Connection failed")

                # Success on 3rd attempt
                mock_response = MagicMock()
                mock_response.json.return_value = {"sessionToken": "session-success"}
                mock_response.raise_for_status = MagicMock()
                return mock_response

            with patch.object(
                client._client, "post", side_effect=mock_post_with_retries  # type: ignore
            ):
                # Should succeed on 3rd attempt
                token = await client.authenticate()
                assert token == "session-success"
                # Verify 3 attempts were made
                assert call_count == 3


@pytest.mark.integration
@pytest.mark.asyncio
async def test_retry_logic_exhausts_attempts():
    """Test that retry logic fails after max attempts."""
    with patch.dict(
        os.environ,
        {
            "CANARY_SAF_BASE_URL": "https://test.canary.com/api/v1",
            "CANARY_VIEWS_BASE_URL": "https://test.canary.com",
            "CANARY_API_TOKEN": "test-token",
            "CANARY_RETRY_ATTEMPTS": "2",
        },
    ):
        async with CanaryAuthClient() as client:
            # Mock all connection failures
            with patch.object(
                client._client,  # type: ignore
                "post",
                side_effect=httpx.ConnectError("Connection failed"),
            ):
                with pytest.raises(CanaryAuthError) as exc_info:
                    await client.authenticate()

                # Verify error message mentions connection issue
                assert "Cannot connect to Canary server" in str(exc_info.value)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_valid_token_auto_refresh():
    """Test that get_valid_token automatically refreshes expired tokens."""
    with patch.dict(
        os.environ,
        {
            "CANARY_SAF_BASE_URL": "https://test.canary.com/api/v1",
            "CANARY_VIEWS_BASE_URL": "https://test.canary.com",
            "CANARY_API_TOKEN": "test-token",
            "CANARY_SESSION_TIMEOUT_MS": "120000",
        },
    ):
        async with CanaryAuthClient() as client:
            # Mock authentication responses
            mock_response = MagicMock()
            mock_response.json.return_value = {"sessionToken": "session-refreshed"}
            mock_response.raise_for_status = MagicMock()

            with patch.object(
                client._client, "post", return_value=mock_response  # type: ignore
            ):
                # Force token to be expired
                client._session_token = None
                client._token_expires_at = None

                token = await client.get_valid_token()
                assert token == "session-refreshed"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_validate_config_success():
    """Test configuration validation with valid setup."""
    with patch.dict(
        os.environ,
        {
            "CANARY_SAF_BASE_URL": "https://test.canary.com/api/v1",
            "CANARY_VIEWS_BASE_URL": "https://test.canary.com",
            "CANARY_API_TOKEN": "test-token",
        },
    ):
        # Mock successful authentication
        mock_response = MagicMock()
        mock_response.json.return_value = {"sessionToken": "session-valid"}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post", return_value=mock_response):
            result = await validate_config()
            assert result is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_validate_config_failure():
    """Test configuration validation with missing credentials."""
    with patch.dict(
        os.environ,
        {
            # Missing required variables
            "CANARY_SAF_BASE_URL": "https://test.canary.com/api/v1",
        },
        clear=True,
    ):
        with pytest.raises(CanaryAuthError) as exc_info:
            await validate_config()

        assert "Missing required credentials" in str(exc_info.value)
