"""Unit tests for Canary authentication module."""

import os
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from canary_mcp.auth import CanaryAuthClient
from canary_mcp.exceptions import CanaryAuthError, ConfigurationError


@pytest.mark.unit
def test_auth_client_initialization():
    """Test that CanaryAuthClient initializes with environment variables."""
    with patch.dict(
        os.environ,
        {
            "CANARY_SAF_BASE_URL": "https://test.canary.com/api/v1",
            "CANARY_VIEWS_BASE_URL": "https://test.canary.com",
            "CANARY_API_TOKEN": "test-token",
            "CANARY_SESSION_TIMEOUT_MS": "60000",
            "CANARY_REQUEST_TIMEOUT_SECONDS": "15",
        },
    ):
        client = CanaryAuthClient()

        assert client.saf_base_url == "https://test.canary.com/api/v1"
        assert client.views_base_url == "https://test.canary.com"
        assert client.user_token == "test-token"
        assert client.session_timeout_ms == 60000
        assert client.request_timeout == 15


@pytest.mark.unit
def test_auth_client_defaults():
    """Test that CanaryAuthClient uses default values when env vars missing."""
    with patch.dict(os.environ, {}, clear=True):
        client = CanaryAuthClient()

        assert client.saf_base_url == ""
        assert client.views_base_url == ""
        assert client.user_token == ""
        assert client.session_timeout_ms == 120000  # default
        assert client.request_timeout == 10  # default


@pytest.mark.unit
def test_validate_credentials_success():
    """Test credential validation passes with all required vars."""
    with patch.dict(
        os.environ,
        {
            "CANARY_SAF_BASE_URL": "https://test.canary.com/api/v1",
            "CANARY_VIEWS_BASE_URL": "https://test.canary.com",
            "CANARY_API_TOKEN": "test-token",
        },
    ):
        client = CanaryAuthClient()
        # Should not raise
        client._validate_credentials()


@pytest.mark.unit
def test_validate_credentials_missing_saf_url():
    """Test credential validation fails when SAF URL missing."""
    with patch.dict(
        os.environ,
        {
            "CANARY_VIEWS_BASE_URL": "https://test.canary.com",
            "CANARY_API_TOKEN": "test-token",
        },
        clear=True,
    ):
        client = CanaryAuthClient()

        with pytest.raises(ConfigurationError) as exc_info:
            client._validate_credentials()

        assert "CANARY_SAF_BASE_URL" in str(exc_info.value)


@pytest.mark.unit
def test_validate_credentials_missing_views_url():
    """Test credential validation fails when Views URL missing."""
    with patch.dict(
        os.environ,
        {
            "CANARY_SAF_BASE_URL": "https://test.canary.com/api/v1",
            "CANARY_API_TOKEN": "test-token",
        },
        clear=True,
    ):
        client = CanaryAuthClient()

        with pytest.raises(ConfigurationError) as exc_info:
            client._validate_credentials()

        assert "CANARY_VIEWS_BASE_URL" in str(exc_info.value)


@pytest.mark.unit
def test_validate_credentials_missing_api_token():
    """Test credential validation fails when API token missing."""
    with patch.dict(
        os.environ,
        {
            "CANARY_SAF_BASE_URL": "https://test.canary.com/api/v1",
            "CANARY_VIEWS_BASE_URL": "https://test.canary.com",
        },
        clear=True,
    ):
        client = CanaryAuthClient()

        with pytest.raises(ConfigurationError) as exc_info:
            client._validate_credentials()

        assert "CANARY_API_TOKEN" in str(exc_info.value)


@pytest.mark.unit
def test_validate_credentials_multiple_missing():
    """Test credential validation shows all missing credentials."""
    with patch.dict(os.environ, {}, clear=True):
        client = CanaryAuthClient()

        with pytest.raises(ConfigurationError) as exc_info:
            client._validate_credentials()

        error_msg = str(exc_info.value)
        assert "CANARY_SAF_BASE_URL" in error_msg
        assert "CANARY_VIEWS_BASE_URL" in error_msg
        assert "CANARY_API_TOKEN" in error_msg


@pytest.mark.unit
def test_is_token_expired_no_token():
    """Test that is_token_expired returns True when no token exists."""
    client = CanaryAuthClient()
    assert client.is_token_expired() is True


@pytest.mark.unit
def test_is_token_expired_no_expiry():
    """Test that is_token_expired returns True when no expiry set."""
    client = CanaryAuthClient()
    client._session_token = "test-token"
    client._token_expires_at = None
    assert client.is_token_expired() is True


@pytest.mark.unit
def test_is_token_expired_already_expired():
    """Test that is_token_expired returns True for expired token."""
    client = CanaryAuthClient()
    client._session_token = "test-token"
    # Set expiry to 1 minute ago
    client._token_expires_at = datetime.now() - timedelta(minutes=1)
    assert client.is_token_expired() is True


@pytest.mark.unit
def test_is_token_expired_expiring_soon():
    """Test that is_token_expired returns True when <30s remaining."""
    client = CanaryAuthClient()
    client._session_token = "test-token"
    # Set expiry to 15 seconds from now
    client._token_expires_at = datetime.now() + timedelta(seconds=15)
    assert client.is_token_expired() is True


@pytest.mark.unit
def test_is_token_expired_valid_token():
    """Test that is_token_expired returns False for valid token with time remaining."""
    client = CanaryAuthClient()
    client._session_token = "test-token"
    # Set expiry to 5 minutes from now
    client._token_expires_at = datetime.now() + timedelta(minutes=5)
    assert client.is_token_expired() is False


@pytest.mark.unit
def test_is_token_expired_boundary_30_seconds():
    """Test token expiry boundary at exactly 30 seconds."""
    client = CanaryAuthClient()
    client._session_token = "test-token"
    # Set expiry to exactly 30 seconds from now
    client._token_expires_at = datetime.now() + timedelta(seconds=30)
    # Should be considered expired (< 30, not <=)
    assert client.is_token_expired() is True


@pytest.mark.unit
def test_is_token_expired_boundary_31_seconds():
    """Test token expiry boundary at 31 seconds (valid)."""
    client = CanaryAuthClient()
    client._session_token = "test-token"
    # Set expiry to 31 seconds from now
    client._token_expires_at = datetime.now() + timedelta(seconds=31)
    # Should be valid
    assert client.is_token_expired() is False
