"""Pytest fixtures for Canary MCP Server tests.

This module provides reusable pytest fixtures for all test scenarios.
Fixtures can be imported into any test file by adding this to conftest.py.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.fixtures.mock_responses import (
    MOCK_GET_AGGREGATES_DICT,
    MOCK_GET_AGGREGATES_LIST,
    MOCK_GET_SERVER_INFO_SUCCESS,
    MOCK_GET_TAG_METADATA_SUCCESS,
    MOCK_GET_TIMEZONES_DICT,
    MOCK_GET_TIMEZONES_LIST,
    MOCK_LIST_NAMESPACES_SUCCESS,
    MOCK_READ_TIMESERIES_SUCCESS,
    MOCK_SEARCH_TAGS_SUCCESS,
)
from tests.fixtures.test_data import (
    SAMPLE_MCP_INFO,
    SAMPLE_NAMESPACES,
    SAMPLE_SERVER_INFO,
    SAMPLE_TAG_METADATA,
    SAMPLE_TAGS,
    SAMPLE_TIMESERIES_DATA,
)


@pytest.fixture
def mock_canary_auth_client():
    """Mock CanaryAuthClient for testing without real API calls.

    Returns:
        AsyncMock: Mock auth client with get_valid_token method
    """
    mock_client = AsyncMock()
    mock_client.get_valid_token = AsyncMock(return_value="test-api-token-123")
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client


@pytest.fixture
def mock_http_client_success():
    """Mock httpx.AsyncClient with successful responses for all endpoints.

    Returns:
        AsyncMock: Mock HTTP client with successful responses
    """
    mock_client = AsyncMock()

    # Create mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"success": True}
    mock_response.raise_for_status = MagicMock()

    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    return mock_client


@pytest.fixture
def sample_namespaces():
    """Sample namespace data for testing.

    Returns:
        list[str]: List of namespace paths
    """
    return SAMPLE_NAMESPACES.copy()


@pytest.fixture
def sample_tags():
    """Sample tag data for testing.

    Returns:
        list[dict]: List of tag dictionaries
    """
    return [tag.copy() for tag in SAMPLE_TAGS]


@pytest.fixture
def sample_tag_metadata():
    """Sample tag metadata for testing.

    Returns:
        dict: Tag metadata dictionary
    """
    return SAMPLE_TAG_METADATA["Maceira.Cement.Kiln6.Temperature.Outlet"].copy()


@pytest.fixture
def sample_timeseries_data():
    """Sample timeseries data points for testing.

    Returns:
        list[dict]: List of timeseries data point dictionaries
    """
    return [point.copy() for point in SAMPLE_TIMESERIES_DATA]


@pytest.fixture
def sample_server_info():
    """Sample server info for testing.

    Returns:
        dict: Server info dictionary
    """
    return SAMPLE_SERVER_INFO.copy()


@pytest.fixture
def sample_mcp_info():
    """Sample MCP info for testing.

    Returns:
        dict: MCP info dictionary
    """
    return SAMPLE_MCP_INFO.copy()


@pytest.fixture
def mock_list_namespaces_response():
    """Mock HTTP response for list_namespaces endpoint.

    Returns:
        MagicMock: Mock HTTP response with namespace data
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_LIST_NAMESPACES_SUCCESS
    mock_response.raise_for_status = MagicMock()
    return mock_response


@pytest.fixture
def mock_search_tags_response():
    """Mock HTTP response for search_tags endpoint.

    Returns:
        MagicMock: Mock HTTP response with tag search results
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_SEARCH_TAGS_SUCCESS
    mock_response.raise_for_status = MagicMock()
    return mock_response


@pytest.fixture
def mock_get_tag_metadata_response():
    """Mock HTTP response for get_tag_metadata endpoint.

    Returns:
        MagicMock: Mock HTTP response with tag metadata
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_GET_TAG_METADATA_SUCCESS
    mock_response.raise_for_status = MagicMock()
    return mock_response


@pytest.fixture
def mock_read_timeseries_response():
    """Mock HTTP response for read_timeseries endpoint.

    Returns:
        MagicMock: Mock HTTP response with timeseries data
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_READ_TIMESERIES_SUCCESS
    mock_response.raise_for_status = MagicMock()
    return mock_response


@pytest.fixture
def mock_get_server_info_response():
    """Mock HTTP response for get_server_info endpoint.

    Returns:
        MagicMock: Mock HTTP response with server info
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_GET_SERVER_INFO_SUCCESS
    mock_response.raise_for_status = MagicMock()
    return mock_response


@pytest.fixture
def mock_get_timezones_dict_response():
    """Mock HTTP response for getTimeZones endpoint (dict format).

    Returns:
        MagicMock: Mock HTTP response with timezones in dict format
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_GET_TIMEZONES_DICT
    mock_response.raise_for_status = MagicMock()
    return mock_response


@pytest.fixture
def mock_get_timezones_list_response():
    """Mock HTTP response for getTimeZones endpoint (list format).

    Returns:
        MagicMock: Mock HTTP response with timezones in list format
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_GET_TIMEZONES_LIST
    mock_response.raise_for_status = MagicMock()
    return mock_response


@pytest.fixture
def mock_get_aggregates_dict_response():
    """Mock HTTP response for getAggregates endpoint (dict format).

    Returns:
        MagicMock: Mock HTTP response with aggregates in dict format
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_GET_AGGREGATES_DICT
    mock_response.raise_for_status = MagicMock()
    return mock_response


@pytest.fixture
def mock_get_aggregates_list_response():
    """Mock HTTP response for getAggregates endpoint (list format).

    Returns:
        MagicMock: Mock HTTP response with aggregates in list format
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_GET_AGGREGATES_LIST
    mock_response.raise_for_status = MagicMock()
    return mock_response


@pytest.fixture
def mock_error_response_401():
    """Mock HTTP 401 Unauthorized error response.

    Returns:
        MagicMock: Mock HTTP response with 401 error
    """
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"
    return mock_response


@pytest.fixture
def mock_error_response_404():
    """Mock HTTP 404 Not Found error response.

    Returns:
        MagicMock: Mock HTTP response with 404 error
    """
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.text = "Not Found"
    return mock_response


@pytest.fixture
def mock_error_response_500():
    """Mock HTTP 500 Internal Server Error response.

    Returns:
        MagicMock: Mock HTTP response with 500 error
    """
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    return mock_response
