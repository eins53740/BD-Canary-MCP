"""Unit tests for read_timeseries MCP tool."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from canary_mcp.server import parse_time_expression, read_timeseries


@pytest.mark.unit
@pytest.mark.asyncio
async def test_read_timeseries_tool_registration():
    """Test that read_timeseries is properly registered as an MCP tool."""
    assert hasattr(read_timeseries, "fn")
    assert callable(read_timeseries.fn)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_read_timeseries_tool_documentation():
    """Test that read_timeseries has proper documentation."""
    assert read_timeseries.fn.__doc__ is not None
    assert "timeseries" in read_timeseries.fn.__doc__.lower()
    assert "historical" in read_timeseries.fn.__doc__.lower()


@pytest.mark.unit
def test_parse_time_expression_iso_timestamp():
    """Test parsing of ISO timestamp (passthrough)."""
    iso_time = "2025-10-30T12:00:00Z"
    result = parse_time_expression(iso_time)
    assert result == iso_time


@pytest.mark.unit
def test_parse_time_expression_yesterday():
    """Test parsing of 'yesterday' expression."""
    result = parse_time_expression("yesterday")
    assert result.endswith("Z")
    # Should be midnight of yesterday
    parsed = datetime.fromisoformat(result.replace("Z", "+00:00"))
    assert parsed.hour == 0
    assert parsed.minute == 0
    assert parsed.second == 0


@pytest.mark.unit
def test_parse_time_expression_last_week():
    """Test parsing of 'last week' expression."""
    result = parse_time_expression("last week")
    assert result.endswith("Z")
    # Should be approximately 7 days ago
    parsed = datetime.fromisoformat(result.replace("Z", "+00:00"))
    now = datetime.now(parsed.tzinfo)
    diff = now - parsed
    assert 6 < diff.days <= 7


@pytest.mark.unit
def test_parse_time_expression_past_24_hours():
    """Test parsing of 'past 24 hours' expression."""
    result = parse_time_expression("past 24 hours")
    assert result.endswith("Z")
    parsed = datetime.fromisoformat(result.replace("Z", "+00:00"))
    now = datetime.now(parsed.tzinfo)
    diff = now - parsed
    assert 0.9 < diff.total_seconds() / 3600 <= 24.1


@pytest.mark.unit
def test_parse_time_expression_last_30_days():
    """Test parsing of 'last 30 days' expression."""
    result = parse_time_expression("last 30 days")
    assert result.endswith("Z")
    parsed = datetime.fromisoformat(result.replace("Z", "+00:00"))
    now = datetime.now(parsed.tzinfo)
    diff = now - parsed
    assert 29 < diff.days <= 30


@pytest.mark.unit
def test_parse_time_expression_now():
    """Test parsing of 'now' expression."""
    result = parse_time_expression("now")
    assert result.endswith("Z")
    parsed = datetime.fromisoformat(result.replace("Z", "+00:00"))
    now = datetime.now(parsed.tzinfo)
    diff = abs((now - parsed).total_seconds())
    assert diff < 2  # Within 2 seconds


@pytest.mark.unit
def test_parse_time_expression_invalid():
    """Test parsing of invalid time expression."""
    with pytest.raises(ValueError) as exc_info:
        parse_time_expression("invalid_expression")
    assert "Unrecognized time expression" in str(exc_info.value)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_read_timeseries_empty_tag_validation():
    """Test that empty tag names are rejected."""
    result = await read_timeseries.fn("", "2025-10-30T00:00:00Z", "2025-10-31T00:00:00Z")

    assert result["success"] is False
    assert "error" in result
    assert "empty" in result["error"].lower()
    assert result["data"] == []
    assert result["count"] == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_read_timeseries_whitespace_tag_validation():
    """Test that whitespace-only tag names are rejected."""
    result = await read_timeseries.fn("   ", "2025-10-30T00:00:00Z", "2025-10-31T00:00:00Z")

    assert result["success"] is False
    assert "error" in result
    assert "empty" in result["error"].lower()
    assert result["data"] == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_read_timeseries_tag_name_normalization():
    """Test that tag names are properly normalized to list."""
    with patch.dict(
        "os.environ",
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

            # Test string input
            result = await read_timeseries.fn(
                "Tag1", "2025-10-30T00:00:00Z", "2025-10-31T00:00:00Z"
            )
            assert result["tag_names"] == ["Tag1"]

            # Test list input
            mock_post.side_effect = [mock_auth_response, mock_data_response]
            result = await read_timeseries.fn(
                ["Tag1", "Tag2"], "2025-10-30T00:00:00Z", "2025-10-31T00:00:00Z"
            )
            assert result["tag_names"] == ["Tag1", "Tag2"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_read_timeseries_time_range_validation():
    """Test that start time must be before end time."""
    result = await read_timeseries.fn(
        "Plant.Tag", "2025-10-31T00:00:00Z", "2025-10-30T00:00:00Z"
    )

    assert result["success"] is False
    assert "error" in result
    assert "before" in result["error"].lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_read_timeseries_data_parsing():
    """Test parsing of timeseries data from API response."""
    with patch.dict(
        "os.environ",
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
                    "value": 100.5,
                    "quality": "Good",
                    "tagName": "Tag1",
                },
                {
                    "timestamp": "2025-10-30T13:00:00Z",
                    "value": 101.2,
                    "quality": "Good",
                    "tagName": "Tag1",
                },
            ]
        }
        mock_data_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = [mock_auth_response, mock_data_response]

            result = await read_timeseries.fn(
                "Tag1", "2025-10-30T00:00:00Z", "2025-10-31T00:00:00Z"
            )

            assert result["success"] is True
            assert result["count"] == 2
            assert len(result["data"]) == 2
            assert result["data"][0]["timestamp"] == "2025-10-30T12:00:00Z"
            assert result["data"][0]["value"] == 100.5
            assert result["data"][0]["quality"] == "Good"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_read_timeseries_response_format_success():
    """Test that successful response has correct format."""
    with patch.dict(
        "os.environ",
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
                "Tag1", "2025-10-30T00:00:00Z", "2025-10-31T00:00:00Z"
            )

            # Verify response structure
            assert "success" in result
            assert "data" in result
            assert "count" in result
            assert "tag_names" in result
            assert "start_time" in result
            assert "end_time" in result
            assert result["success"] is True
            assert isinstance(result["data"], list)
            assert isinstance(result["count"], int)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_read_timeseries_response_format_error():
    """Test that error response has correct format."""
    result = await read_timeseries.fn("", "2025-10-30T00:00:00Z", "2025-10-31T00:00:00Z")

    # Verify error response structure
    assert "success" in result
    assert "error" in result
    assert "data" in result
    assert "count" in result
    assert result["success"] is False
    assert isinstance(result["error"], str)
    assert result["data"] == []
    assert result["count"] == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_read_timeseries_error_message_formatting():
    """Test that error messages are properly formatted."""
    # Test empty tag error
    result = await read_timeseries.fn("", "2025-10-30T00:00:00Z", "2025-10-31T00:00:00Z")
    assert "empty" in result["error"].lower()

    # Test invalid time expression
    result = await read_timeseries.fn("Tag1", "invalid", "2025-10-31T00:00:00Z")
    assert "time expression" in result["error"].lower()

    # Test time range validation
    result = await read_timeseries.fn("Tag1", "2025-10-31T00:00:00Z", "2025-10-30T00:00:00Z")
    assert "before" in result["error"].lower()
