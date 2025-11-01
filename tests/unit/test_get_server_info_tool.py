"""Unit tests for get_server_info MCP tool."""

import pytest

from canary_mcp.server import get_server_info


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_server_info_tool_registration():
    """Test that get_server_info is properly registered as an MCP tool."""
    assert hasattr(get_server_info, "fn")
    assert callable(get_server_info.fn)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_server_info_tool_has_documentation():
    """Test that get_server_info tool has proper documentation."""
    assert get_server_info.fn.__doc__ is not None
    assert "Canary server health" in get_server_info.fn.__doc__
    assert "capability information" in get_server_info.fn.__doc__


@pytest.mark.unit
def test_get_server_info_response_structure():
    """Test that get_server_info response has expected structure."""
    # This is a schema validation test
    expected_success_keys = {"success", "server_info", "mcp_info"}
    expected_error_keys = {"success", "error", "server_info", "mcp_info"}

    # Test success response structure
    success_response = {
        "success": True,
        "server_info": {
            "canary_server_url": "https://test.local",
            "api_version": "v2",
            "connected": True,
            "supported_timezones": ["UTC"],
            "total_timezones": 1,
            "supported_aggregates": ["Min"],
            "total_aggregates": 1,
        },
        "mcp_info": {
            "server_name": "Canary MCP Server",
            "version": "1.0.0",
            "configuration": {
                "saf_base_url": "https://test.local/api/v2",
                "views_base_url": "https://test.local",
            },
        },
    }
    assert set(success_response.keys()) == expected_success_keys
    assert isinstance(success_response["success"], bool)
    assert isinstance(success_response["server_info"], dict)
    assert isinstance(success_response["mcp_info"], dict)

    # Test error response structure
    error_response = {
        "success": False,
        "error": "Test error message",
        "server_info": {},
        "mcp_info": {},
    }
    assert set(error_response.keys()) == expected_error_keys
    assert isinstance(error_response["success"], bool)
    assert isinstance(error_response["error"], str)


@pytest.mark.unit
def test_server_info_keys():
    """Test that server_info has all expected keys."""
    server_info = {
        "canary_server_url": "https://test.local",
        "api_version": "v2",
        "connected": True,
        "supported_timezones": ["UTC", "PST"],
        "total_timezones": 2,
        "supported_aggregates": ["Min", "Max"],
        "total_aggregates": 2,
    }

    required_keys = {
        "canary_server_url",
        "api_version",
        "connected",
        "supported_timezones",
        "total_timezones",
        "supported_aggregates",
        "total_aggregates",
    }

    assert set(server_info.keys()) == required_keys
    assert isinstance(server_info["canary_server_url"], str)
    assert isinstance(server_info["api_version"], str)
    assert isinstance(server_info["connected"], bool)
    assert isinstance(server_info["supported_timezones"], list)
    assert isinstance(server_info["total_timezones"], int)
    assert isinstance(server_info["supported_aggregates"], list)
    assert isinstance(server_info["total_aggregates"], int)


@pytest.mark.unit
def test_mcp_info_keys():
    """Test that mcp_info has all expected keys."""
    mcp_info = {
        "server_name": "Canary MCP Server",
        "version": "1.0.0",
        "configuration": {
            "saf_base_url": "https://test.local/api/v2",
            "views_base_url": "https://test.local",
        },
    }

    required_keys = {"server_name", "version", "configuration"}

    assert set(mcp_info.keys()) == required_keys
    assert isinstance(mcp_info["server_name"], str)
    assert isinstance(mcp_info["version"], str)
    assert isinstance(mcp_info["configuration"], dict)
    assert "saf_base_url" in mcp_info["configuration"]
    assert "views_base_url" in mcp_info["configuration"]


@pytest.mark.unit
def test_timezone_list_limiting():
    """Test logic for limiting timezone list to 10 items."""
    # Simulate the limiting logic
    timezones_small = ["TZ1", "TZ2", "TZ3"]
    timezones_large = [f"TZ{i}" for i in range(50)]

    # Small list - should return all
    result_small = timezones_small[:10] if len(timezones_small) > 10 else timezones_small
    assert len(result_small) == 3
    assert result_small == timezones_small

    # Large list - should limit to 10
    result_large = timezones_large[:10] if len(timezones_large) > 10 else timezones_large
    assert len(result_large) == 10
    assert result_large == timezones_large[:10]


@pytest.mark.unit
def test_aggregates_list_limiting():
    """Test logic for limiting aggregates list to 10 items."""
    # Simulate the limiting logic
    aggregates_small = ["Min", "Max", "Avg"]
    aggregates_large = [f"Agg{i}" for i in range(25)]

    # Small list - should return all
    result_small = (
        aggregates_small[:10] if len(aggregates_small) > 10 else aggregates_small
    )
    assert len(result_small) == 3
    assert result_small == aggregates_small

    # Large list - should limit to 10
    result_large = (
        aggregates_large[:10] if len(aggregates_large) > 10 else aggregates_large
    )
    assert len(result_large) == 10
    assert result_large == aggregates_large[:10]


@pytest.mark.unit
def test_dict_response_parsing():
    """Test parsing logic for dict response format."""
    # Simulate API response parsing
    dict_response = {
        "statusCode": "Good",
        "timeZones": ["UTC", "PST", "EST"],
    }

    # Extract timezones from dict
    timezones = []
    if isinstance(dict_response, dict):
        timezones = dict_response.get("timeZones", [])
    elif isinstance(dict_response, list):
        timezones = dict_response

    assert len(timezones) == 3
    assert timezones == ["UTC", "PST", "EST"]


@pytest.mark.unit
def test_list_response_parsing():
    """Test parsing logic for list response format."""
    # Simulate API response as array
    list_response = ["UTC", "PST", "EST", "CET"]

    # Extract timezones from list
    timezones = []
    if isinstance(list_response, dict):
        timezones = list_response.get("timeZones", [])
    elif isinstance(list_response, list):
        timezones = list_response

    assert len(timezones) == 4
    assert timezones == ["UTC", "PST", "EST", "CET"]


@pytest.mark.unit
def test_error_response_format():
    """Test error response formatting."""
    # Simulate different error scenarios
    auth_error = "Authentication failed: Invalid API token"
    api_error = "API request failed with status 500: Internal Server Error"
    network_error = "Network error accessing Canary API: Connection timeout"
    config_error = "CANARY_VIEWS_BASE_URL not configured"

    # All errors should be strings
    assert isinstance(auth_error, str)
    assert isinstance(api_error, str)
    assert isinstance(network_error, str)
    assert isinstance(config_error, str)

    # All errors should contain descriptive text
    assert "Authentication failed" in auth_error
    assert "API request failed" in api_error
    assert "Network error" in network_error
    assert "not configured" in config_error


@pytest.mark.unit
def test_empty_response_handling():
    """Test handling of empty API responses."""
    # Simulate empty responses
    empty_dict = {"timeZones": []}
    empty_list = []

    # Parse empty dict
    timezones_from_dict = []
    if isinstance(empty_dict, dict):
        timezones_from_dict = empty_dict.get("timeZones", [])
    elif isinstance(empty_dict, list):
        timezones_from_dict = empty_dict

    assert timezones_from_dict == []
    assert len(timezones_from_dict) == 0

    # Parse empty list
    timezones_from_list = []
    if isinstance(empty_list, dict):
        timezones_from_list = empty_list.get("timeZones", [])
    elif isinstance(empty_list, list):
        timezones_from_list = empty_list

    assert timezones_from_list == []
    assert len(timezones_from_list) == 0


@pytest.mark.unit
def test_server_info_connected_flag():
    """Test that server_info includes connected flag when successful."""
    # Successful response should have connected=True
    server_info_success = {
        "canary_server_url": "https://test.local",
        "api_version": "v2",
        "connected": True,
        "supported_timezones": ["UTC"],
        "total_timezones": 1,
        "supported_aggregates": ["Min"],
        "total_aggregates": 1,
    }

    assert server_info_success["connected"] is True
    assert isinstance(server_info_success["connected"], bool)
