"""Unit tests for get_tag_metadata MCP tool."""

from unittest.mock import MagicMock, patch

import pytest

from canary_mcp.server import get_tag_metadata


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_tag_metadata_tool_registration():
    """Test that get_tag_metadata is properly registered as an MCP tool."""
    assert hasattr(get_tag_metadata, "fn")
    assert callable(get_tag_metadata.fn)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_tag_metadata_tool_documentation():
    """Test that get_tag_metadata has proper documentation."""
    assert get_tag_metadata.fn.__doc__ is not None
    assert "metadata" in get_tag_metadata.fn.__doc__.lower()
    assert "tag" in get_tag_metadata.fn.__doc__.lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_tag_metadata_empty_tag_path_validation():
    """Test that empty tag path is rejected."""
    result = await get_tag_metadata.fn("")

    assert result["success"] is False
    assert "error" in result
    assert "empty" in result["error"].lower()
    assert result["metadata"] == {}
    assert result["tag_path"] == ""


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_tag_metadata_whitespace_tag_path_validation():
    """Test that whitespace-only tag path is rejected."""
    result = await get_tag_metadata.fn("   ")

    assert result["success"] is False
    assert "error" in result
    assert "empty" in result["error"].lower()
    assert result["metadata"] == {}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_tag_metadata_data_parsing_valid_response():
    """Test parsing of valid metadata from API response."""
    mock_response_data = {
        "name": "Temperature",
        "path": "Plant.Area1.Temperature",
        "dataType": "float",
        "description": "Temperature sensor",
        "units": "°C",
        "minValue": 0,
        "maxValue": 1500,
        "updateRate": 1000,
        "properties": {
            "quality": "Good",
            "timestamp": "2025-10-31T12:00:00Z",
        },
    }

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

        mock_metadata_response = MagicMock()
        mock_metadata_response.json.return_value = mock_response_data
        mock_metadata_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = [mock_auth_response, mock_metadata_response]

            result = await get_tag_metadata.fn("Plant.Area1.Temperature")

            assert result["success"] is True
            assert result["tag_path"] == "Plant.Area1.Temperature"
            assert result["metadata"]["name"] == "Temperature"
            assert result["metadata"]["path"] == "Plant.Area1.Temperature"
            assert result["metadata"]["dataType"] == "float"
            assert result["metadata"]["units"] == "°C"
            assert result["metadata"]["minValue"] == 0
            assert result["metadata"]["maxValue"] == 1500
            assert result["metadata"]["updateRate"] == 1000
            assert "properties" in result["metadata"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_tag_metadata_data_parsing_missing_fields():
    """Test parsing of metadata with missing optional fields."""
    mock_response_data = {
        "tagName": "SimpleTag",
        "type": "int",
        # Missing most optional fields
    }

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

        mock_metadata_response = MagicMock()
        mock_metadata_response.json.return_value = mock_response_data
        mock_metadata_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = [mock_auth_response, mock_metadata_response]

            result = await get_tag_metadata.fn("Plant.SimpleTag")

            assert result["success"] is True
            assert result["metadata"]["name"] == "SimpleTag"
            assert result["metadata"]["dataType"] == "int"
            assert result["metadata"]["description"] == ""
            assert result["metadata"]["units"] == ""
            assert result["metadata"]["minValue"] is None
            assert result["metadata"]["maxValue"] is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_tag_metadata_data_parsing_empty_response():
    """Test parsing of empty or minimal response."""
    mock_response_data = {}

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

        mock_metadata_response = MagicMock()
        mock_metadata_response.json.return_value = mock_response_data
        mock_metadata_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = [mock_auth_response, mock_metadata_response]

            result = await get_tag_metadata.fn("Plant.Tag")

            assert result["success"] is True
            assert result["metadata"]["name"] == ""
            assert result["metadata"]["dataType"] == "unknown"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_tag_metadata_response_format_success():
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

        mock_metadata_response = MagicMock()
        mock_metadata_response.json.return_value = {"name": "Tag1"}
        mock_metadata_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = [mock_auth_response, mock_metadata_response]

            result = await get_tag_metadata.fn("Plant.Tag1")

            # Verify response structure
            assert "success" in result
            assert "metadata" in result
            assert "tag_path" in result
            assert result["success"] is True
            assert isinstance(result["metadata"], dict)
            assert result["tag_path"] == "Plant.Tag1"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_tag_metadata_response_format_error():
    """Test that error response has correct format."""
    result = await get_tag_metadata.fn("")

    # Verify error response structure
    assert "success" in result
    assert "error" in result
    assert "metadata" in result
    assert "tag_path" in result
    assert result["success"] is False
    assert isinstance(result["error"], str)
    assert result["metadata"] == {}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_tag_metadata_error_message_formatting():
    """Test that error messages are properly formatted."""
    # Test empty tag path error
    result = await get_tag_metadata.fn("")
    assert "empty" in result["error"].lower()

    # Test whitespace tag path error
    result = await get_tag_metadata.fn("   ")
    assert "empty" in result["error"].lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_tag_metadata_with_properties():
    """Test that additional properties are included when present."""
    mock_response_data = {
        "name": "Pressure",
        "dataType": "float",
        "properties": {
            "alarmHigh": 100,
            "alarmLow": 10,
            "quality": "Good",
        },
    }

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

        mock_metadata_response = MagicMock()
        mock_metadata_response.json.return_value = mock_response_data
        mock_metadata_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = [mock_auth_response, mock_metadata_response]

            result = await get_tag_metadata.fn("Plant.Pressure")

            assert result["success"] is True
            assert "properties" in result["metadata"]
            assert result["metadata"]["properties"]["alarmHigh"] == 100
            assert result["metadata"]["properties"]["alarmLow"] == 10
