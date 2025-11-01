"""Mock Canary API HTTP responses for testing.

This module provides mock HTTP responses for all Canary API endpoints
used by the 5 MCP tools. Responses match Read API v2 format.
"""

from tests.fixtures.test_data import (
    SAMPLE_AGGREGATES_LIST,
    SAMPLE_MCP_INFO,
    SAMPLE_NAMESPACES,
    SAMPLE_SERVER_INFO,
    SAMPLE_TAG_METADATA,
    SAMPLE_TAGS,
    SAMPLE_TIMESERIES_DATA,
    SAMPLE_TIMESERIES_WITH_QUALITY_ISSUES,
    SAMPLE_TIMEZONES_LIST,
)

# Mock Response: list_namespaces (Story 1.3)
MOCK_LIST_NAMESPACES_SUCCESS = {
    "success": True,
    "namespaces": SAMPLE_NAMESPACES,
    "count": len(SAMPLE_NAMESPACES),
}

# Mock Response: search_tags (Story 1.4)
MOCK_SEARCH_TAGS_SUCCESS = {
    "success": True,
    "tags": SAMPLE_TAGS,
    "count": len(SAMPLE_TAGS),
    "pattern": "temperature",
}

MOCK_SEARCH_TAGS_NO_RESULTS = {
    "success": True,
    "tags": [],
    "count": 0,
    "pattern": "nonexistent",
}

# Mock Response: get_tag_metadata (Story 1.5)
MOCK_GET_TAG_METADATA_SUCCESS = {
    "success": True,
    "metadata": SAMPLE_TAG_METADATA["Maceira.Cement.Kiln6.Temperature.Outlet"],
    "tag_path": "Maceira.Cement.Kiln6.Temperature.Outlet",
}

MOCK_GET_TAG_METADATA_NOT_FOUND = {
    "success": False,
    "error": "Tag 'Invalid.Tag' not found",
    "metadata": {},
    "tag_path": "Invalid.Tag",
}

# Mock Response: read_timeseries (Story 1.6)
MOCK_READ_TIMESERIES_SUCCESS = {
    "success": True,
    "data": SAMPLE_TIMESERIES_DATA,
    "count": len(SAMPLE_TIMESERIES_DATA),
    "tag_names": ["Maceira.Cement.Kiln6.Temperature.Outlet"],
    "start_time": "2025-10-31T10:00:00Z",
    "end_time": "2025-10-31T10:05:00Z",
}

MOCK_READ_TIMESERIES_WITH_QUALITY_ISSUES = {
    "success": True,
    "data": SAMPLE_TIMESERIES_WITH_QUALITY_ISSUES,
    "count": len(SAMPLE_TIMESERIES_WITH_QUALITY_ISSUES),
    "tag_names": ["Maceira.Cement.Kiln6.Temperature.Outlet"],
    "start_time": "2025-10-31T10:00:00Z",
    "end_time": "2025-10-31T10:03:00Z",
}

MOCK_READ_TIMESERIES_EMPTY = {
    "success": True,
    "data": [],
    "count": 0,
    "tag_names": ["Maceira.Cement.Kiln6.Temperature.Outlet"],
    "start_time": "2025-10-30T00:00:00Z",
    "end_time": "2025-10-30T01:00:00Z",
}

MOCK_READ_TIMESERIES_TAG_NOT_FOUND = {
    "success": False,
    "error": "Tag not found: Invalid.Tag",
    "data": [],
    "count": 0,
    "tag_names": ["Invalid.Tag"],
}

# Mock Response: get_server_info (Story 1.7)
MOCK_GET_SERVER_INFO_SUCCESS = {
    "success": True,
    "server_info": SAMPLE_SERVER_INFO,
    "mcp_info": SAMPLE_MCP_INFO,
}

# Alternative Response Formats (Read API v2 variations)
# Some endpoints return data directly in dict with specific keys
MOCK_GET_TIMEZONES_DICT = {
    "statusCode": "Good",
    "timeZones": SAMPLE_TIMEZONES_LIST,
}

# Some endpoints return lists directly
MOCK_GET_TIMEZONES_LIST = SAMPLE_TIMEZONES_LIST

MOCK_GET_AGGREGATES_DICT = {
    "statusCode": "Good",
    "aggregates": SAMPLE_AGGREGATES_LIST,
}

MOCK_GET_AGGREGATES_LIST = SAMPLE_AGGREGATES_LIST

# Error Response Templates
MOCK_AUTH_ERROR = {
    "success": False,
    "error": "Authentication failed: Invalid API token",
}

MOCK_API_ERROR_500 = {
    "success": False,
    "error": "API request failed with status 500: Internal Server Error",
}

MOCK_NETWORK_ERROR = {
    "success": False,
    "error": "Network error accessing Canary API: Connection timeout",
}

MOCK_CONFIG_ERROR = {
    "success": False,
    "error": "CANARY_VIEWS_BASE_URL not configured",
}

MOCK_MALFORMED_RESPONSE = {
    "unexpected_field": "This is not the expected format",
    "missing": "required fields",
}
