"""Unit tests validating test fixtures and mock responses.

This test suite ensures all fixtures load correctly, validate against
expected formats, and provide consistent data for other tests.
"""

import pytest

from tests.fixtures.mock_responses import (
    MOCK_API_ERROR_500,
    MOCK_AUTH_ERROR,
    MOCK_CONFIG_ERROR,
    MOCK_GET_AGGREGATES_DICT,
    MOCK_GET_AGGREGATES_LIST,
    MOCK_GET_SERVER_INFO_SUCCESS,
    MOCK_GET_TAG_METADATA_NOT_FOUND,
    MOCK_GET_TAG_METADATA_SUCCESS,
    MOCK_GET_TIMEZONES_DICT,
    MOCK_GET_TIMEZONES_LIST,
    MOCK_LIST_NAMESPACES_SUCCESS,
    MOCK_MALFORMED_RESPONSE,
    MOCK_NETWORK_ERROR,
    MOCK_READ_TIMESERIES_EMPTY,
    MOCK_READ_TIMESERIES_SUCCESS,
    MOCK_READ_TIMESERIES_TAG_NOT_FOUND,
    MOCK_READ_TIMESERIES_WITH_QUALITY_ISSUES,
    MOCK_SEARCH_TAGS_NO_RESULTS,
    MOCK_SEARCH_TAGS_SUCCESS,
)
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


@pytest.mark.unit
def test_sample_namespaces_loads():
    """Test that sample namespace data loads without errors."""
    assert SAMPLE_NAMESPACES is not None
    assert isinstance(SAMPLE_NAMESPACES, list)
    assert len(SAMPLE_NAMESPACES) > 0
    assert all(isinstance(ns, str) for ns in SAMPLE_NAMESPACES)


@pytest.mark.unit
def test_sample_tags_loads():
    """Test that sample tag data loads without errors."""
    assert SAMPLE_TAGS is not None
    assert isinstance(SAMPLE_TAGS, list)
    assert len(SAMPLE_TAGS) > 0
    for tag in SAMPLE_TAGS:
        assert "name" in tag
        assert "path" in tag
        assert "dataType" in tag


@pytest.mark.unit
def test_sample_tag_metadata_loads():
    """Test that sample tag metadata loads without errors."""
    assert SAMPLE_TAG_METADATA is not None
    assert isinstance(SAMPLE_TAG_METADATA, dict)
    assert len(SAMPLE_TAG_METADATA) > 0
    for tag_path, metadata in SAMPLE_TAG_METADATA.items():
        assert "name" in metadata
        assert "dataType" in metadata
        assert "units" in metadata


@pytest.mark.unit
def test_sample_timeseries_data_loads():
    """Test that sample timeseries data loads without errors."""
    assert SAMPLE_TIMESERIES_DATA is not None
    assert isinstance(SAMPLE_TIMESERIES_DATA, list)
    assert len(SAMPLE_TIMESERIES_DATA) > 0
    for point in SAMPLE_TIMESERIES_DATA:
        assert "timestamp" in point
        assert "value" in point
        assert "quality" in point
        assert "tagName" in point


@pytest.mark.unit
def test_sample_server_info_loads():
    """Test that sample server info loads without errors."""
    assert SAMPLE_SERVER_INFO is not None
    assert isinstance(SAMPLE_SERVER_INFO, dict)
    assert "canary_server_url" in SAMPLE_SERVER_INFO
    assert "api_version" in SAMPLE_SERVER_INFO
    assert "connected" in SAMPLE_SERVER_INFO


@pytest.mark.unit
def test_mock_list_namespaces_success_structure():
    """Test list_namespaces mock response has expected structure."""
    assert MOCK_LIST_NAMESPACES_SUCCESS is not None
    assert "success" in MOCK_LIST_NAMESPACES_SUCCESS
    assert "namespaces" in MOCK_LIST_NAMESPACES_SUCCESS
    assert "count" in MOCK_LIST_NAMESPACES_SUCCESS
    assert MOCK_LIST_NAMESPACES_SUCCESS["success"] is True
    assert isinstance(MOCK_LIST_NAMESPACES_SUCCESS["namespaces"], list)


@pytest.mark.unit
def test_mock_search_tags_success_structure():
    """Test search_tags mock response has expected structure."""
    assert MOCK_SEARCH_TAGS_SUCCESS is not None
    assert "success" in MOCK_SEARCH_TAGS_SUCCESS
    assert "tags" in MOCK_SEARCH_TAGS_SUCCESS
    assert "count" in MOCK_SEARCH_TAGS_SUCCESS
    assert "pattern" in MOCK_SEARCH_TAGS_SUCCESS
    assert MOCK_SEARCH_TAGS_SUCCESS["success"] is True
    assert isinstance(MOCK_SEARCH_TAGS_SUCCESS["tags"], list)


@pytest.mark.unit
def test_mock_search_tags_no_results_structure():
    """Test search_tags empty result mock has expected structure."""
    assert MOCK_SEARCH_TAGS_NO_RESULTS is not None
    assert "success" in MOCK_SEARCH_TAGS_NO_RESULTS
    assert "tags" in MOCK_SEARCH_TAGS_NO_RESULTS
    assert MOCK_SEARCH_TAGS_NO_RESULTS["success"] is True
    assert MOCK_SEARCH_TAGS_NO_RESULTS["count"] == 0
    assert len(MOCK_SEARCH_TAGS_NO_RESULTS["tags"]) == 0


@pytest.mark.unit
def test_mock_get_tag_metadata_success_structure():
    """Test get_tag_metadata mock response has expected structure."""
    assert MOCK_GET_TAG_METADATA_SUCCESS is not None
    assert "success" in MOCK_GET_TAG_METADATA_SUCCESS
    assert "metadata" in MOCK_GET_TAG_METADATA_SUCCESS
    assert "tag_path" in MOCK_GET_TAG_METADATA_SUCCESS
    assert MOCK_GET_TAG_METADATA_SUCCESS["success"] is True
    assert isinstance(MOCK_GET_TAG_METADATA_SUCCESS["metadata"], dict)


@pytest.mark.unit
def test_mock_get_tag_metadata_not_found_structure():
    """Test get_tag_metadata not found mock has expected error structure."""
    assert MOCK_GET_TAG_METADATA_NOT_FOUND is not None
    assert "success" in MOCK_GET_TAG_METADATA_NOT_FOUND
    assert "error" in MOCK_GET_TAG_METADATA_NOT_FOUND
    assert MOCK_GET_TAG_METADATA_NOT_FOUND["success"] is False
    assert isinstance(MOCK_GET_TAG_METADATA_NOT_FOUND["error"], str)


@pytest.mark.unit
def test_mock_read_timeseries_success_structure():
    """Test read_timeseries mock response has expected structure."""
    assert MOCK_READ_TIMESERIES_SUCCESS is not None
    assert "success" in MOCK_READ_TIMESERIES_SUCCESS
    assert "data" in MOCK_READ_TIMESERIES_SUCCESS
    assert "count" in MOCK_READ_TIMESERIES_SUCCESS
    assert "tag_names" in MOCK_READ_TIMESERIES_SUCCESS
    assert "start_time" in MOCK_READ_TIMESERIES_SUCCESS
    assert "end_time" in MOCK_READ_TIMESERIES_SUCCESS
    assert MOCK_READ_TIMESERIES_SUCCESS["success"] is True
    assert isinstance(MOCK_READ_TIMESERIES_SUCCESS["data"], list)


@pytest.mark.unit
def test_mock_read_timeseries_with_quality_issues():
    """Test timeseries mock with quality issues has varied quality flags."""
    assert MOCK_READ_TIMESERIES_WITH_QUALITY_ISSUES is not None
    data = MOCK_READ_TIMESERIES_WITH_QUALITY_ISSUES["data"]
    assert len(data) > 0

    # Verify quality flags vary (not all "Good")
    quality_flags = {point["quality"] for point in data}
    assert len(quality_flags) > 1  # Multiple different quality flags


@pytest.mark.unit
def test_mock_read_timeseries_empty_structure():
    """Test read_timeseries empty result mock has expected structure."""
    assert MOCK_READ_TIMESERIES_EMPTY is not None
    assert "success" in MOCK_READ_TIMESERIES_EMPTY
    assert "data" in MOCK_READ_TIMESERIES_EMPTY
    assert MOCK_READ_TIMESERIES_EMPTY["success"] is True
    assert MOCK_READ_TIMESERIES_EMPTY["count"] == 0
    assert len(MOCK_READ_TIMESERIES_EMPTY["data"]) == 0


@pytest.mark.unit
def test_mock_read_timeseries_tag_not_found():
    """Test read_timeseries tag not found mock has expected error structure."""
    assert MOCK_READ_TIMESERIES_TAG_NOT_FOUND is not None
    assert "success" in MOCK_READ_TIMESERIES_TAG_NOT_FOUND
    assert "error" in MOCK_READ_TIMESERIES_TAG_NOT_FOUND
    assert MOCK_READ_TIMESERIES_TAG_NOT_FOUND["success"] is False


@pytest.mark.unit
def test_mock_get_server_info_success_structure():
    """Test get_server_info mock response has expected structure."""
    assert MOCK_GET_SERVER_INFO_SUCCESS is not None
    assert "success" in MOCK_GET_SERVER_INFO_SUCCESS
    assert "server_info" in MOCK_GET_SERVER_INFO_SUCCESS
    assert "mcp_info" in MOCK_GET_SERVER_INFO_SUCCESS
    assert MOCK_GET_SERVER_INFO_SUCCESS["success"] is True

    server_info = MOCK_GET_SERVER_INFO_SUCCESS["server_info"]
    assert "canary_server_url" in server_info
    assert "api_version" in server_info
    assert "supported_timezones" in server_info
    assert "supported_aggregates" in server_info

    mcp_info = MOCK_GET_SERVER_INFO_SUCCESS["mcp_info"]
    assert "server_name" in mcp_info
    assert "version" in mcp_info


@pytest.mark.unit
def test_mock_get_timezones_dict_format():
    """Test getTimeZones dict format mock has expected structure."""
    assert MOCK_GET_TIMEZONES_DICT is not None
    assert "timeZones" in MOCK_GET_TIMEZONES_DICT
    assert isinstance(MOCK_GET_TIMEZONES_DICT["timeZones"], list)


@pytest.mark.unit
def test_mock_get_timezones_list_format():
    """Test getTimeZones list format mock is a list."""
    assert MOCK_GET_TIMEZONES_LIST is not None
    assert isinstance(MOCK_GET_TIMEZONES_LIST, list)
    assert len(MOCK_GET_TIMEZONES_LIST) > 0


@pytest.mark.unit
def test_mock_get_aggregates_dict_format():
    """Test getAggregates dict format mock has expected structure."""
    assert MOCK_GET_AGGREGATES_DICT is not None
    assert "aggregates" in MOCK_GET_AGGREGATES_DICT
    assert isinstance(MOCK_GET_AGGREGATES_DICT["aggregates"], list)


@pytest.mark.unit
def test_mock_get_aggregates_list_format():
    """Test getAggregates list format mock is a list."""
    assert MOCK_GET_AGGREGATES_LIST is not None
    assert isinstance(MOCK_GET_AGGREGATES_LIST, list)
    assert len(MOCK_GET_AGGREGATES_LIST) > 0


@pytest.mark.unit
def test_mock_auth_error_structure():
    """Test authentication error mock has expected structure."""
    assert MOCK_AUTH_ERROR is not None
    assert "success" in MOCK_AUTH_ERROR
    assert "error" in MOCK_AUTH_ERROR
    assert MOCK_AUTH_ERROR["success"] is False
    assert "Authentication failed" in MOCK_AUTH_ERROR["error"]


@pytest.mark.unit
def test_mock_api_error_500_structure():
    """Test API 500 error mock has expected structure."""
    assert MOCK_API_ERROR_500 is not None
    assert "success" in MOCK_API_ERROR_500
    assert "error" in MOCK_API_ERROR_500
    assert MOCK_API_ERROR_500["success"] is False
    assert "500" in MOCK_API_ERROR_500["error"]


@pytest.mark.unit
def test_mock_network_error_structure():
    """Test network error mock has expected structure."""
    assert MOCK_NETWORK_ERROR is not None
    assert "success" in MOCK_NETWORK_ERROR
    assert "error" in MOCK_NETWORK_ERROR
    assert MOCK_NETWORK_ERROR["success"] is False
    assert "Network error" in MOCK_NETWORK_ERROR["error"]


@pytest.mark.unit
def test_mock_config_error_structure():
    """Test configuration error mock has expected structure."""
    assert MOCK_CONFIG_ERROR is not None
    assert "success" in MOCK_CONFIG_ERROR
    assert "error" in MOCK_CONFIG_ERROR
    assert MOCK_CONFIG_ERROR["success"] is False
    assert "not configured" in MOCK_CONFIG_ERROR["error"]


@pytest.mark.unit
def test_mock_malformed_response():
    """Test malformed response mock has unexpected structure."""
    assert MOCK_MALFORMED_RESPONSE is not None
    assert "unexpected_field" in MOCK_MALFORMED_RESPONSE
    # Should NOT have standard fields
    assert "success" not in MOCK_MALFORMED_RESPONSE


@pytest.mark.unit
def test_all_5_mcp_tools_covered():
    """Test that fixtures cover all 5 MCP tools."""
    # Verify we have success mocks for all 5 tools
    assert MOCK_LIST_NAMESPACES_SUCCESS is not None  # Tool 1
    assert MOCK_SEARCH_TAGS_SUCCESS is not None  # Tool 2
    assert MOCK_GET_TAG_METADATA_SUCCESS is not None  # Tool 3
    assert MOCK_READ_TIMESERIES_SUCCESS is not None  # Tool 4
    assert MOCK_GET_SERVER_INFO_SUCCESS is not None  # Tool 5


@pytest.mark.unit
def test_fixtures_use_maceira_data():
    """Test that fixtures use realistic Maceira plant data."""
    # Check namespaces include Maceira
    assert any("Maceira" in ns for ns in SAMPLE_NAMESPACES)

    # Check tags include Maceira paths
    assert any("Maceira" in tag["path"] for tag in SAMPLE_TAGS)

    # Check server info uses correct URL
    assert "scunscanary.secil.pt" in SAMPLE_SERVER_INFO["canary_server_url"]


@pytest.mark.unit
def test_pytest_fixtures_can_be_imported():
    """Test that pytest fixtures module can be imported."""
    # This import will fail if conftest_fixtures.py has syntax errors
    from tests.fixtures import conftest_fixtures

    assert conftest_fixtures is not None


@pytest.mark.unit
def test_sample_data_consistency():
    """Test that sample data is internally consistent."""
    # Tag metadata keys should match tag paths
    for tag_path in SAMPLE_TAG_METADATA.keys():
        metadata = SAMPLE_TAG_METADATA[tag_path]
        assert metadata["path"] == tag_path

    # Timeseries data should reference known tags
    for point in SAMPLE_TIMESERIES_DATA:
        tag_name = point["tagName"]
        # Should be a valid-looking tag path
        assert "." in tag_name  # Has namespace structure


@pytest.mark.unit
def test_error_scenarios_have_proper_formats():
    """Test that all error scenario mocks have success=False."""
    error_mocks = [
        MOCK_GET_TAG_METADATA_NOT_FOUND,
        MOCK_READ_TIMESERIES_TAG_NOT_FOUND,
        MOCK_AUTH_ERROR,
        MOCK_API_ERROR_500,
        MOCK_NETWORK_ERROR,
        MOCK_CONFIG_ERROR,
    ]

    for error_mock in error_mocks:
        assert "success" in error_mock
        assert error_mock["success"] is False
        assert "error" in error_mock
        assert isinstance(error_mock["error"], str)
        assert len(error_mock["error"]) > 0
