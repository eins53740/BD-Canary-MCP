"""Unit tests for search_tags MCP tool."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from canary_mcp.server import search_tags


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_tags_tool_registration():
    """Test that search_tags is properly registered as an MCP tool."""
    assert hasattr(search_tags, "fn")
    assert callable(search_tags.fn)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_tags_tool_documentation():
    """Test that search_tags has proper documentation."""
    assert search_tags.fn.__doc__ is not None
    assert "search" in search_tags.fn.__doc__.lower()
    assert "tag" in search_tags.fn.__doc__.lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_tags_empty_pattern_validation():
    """Test that empty search pattern is rejected."""
    result = await search_tags.fn("")

    assert result["success"] is False
    assert "error" in result
    assert "empty" in result["error"].lower()
    assert result["tags"] == []
    assert result["count"] == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_tags_whitespace_pattern_validation():
    """Test that whitespace-only pattern is rejected."""
    result = await search_tags.fn("   ")

    assert result["success"] is False
    assert "error" in result
    assert "empty" in result["error"].lower()
    assert result["tags"] == []
    assert result["count"] == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_tags_data_parsing_valid_response():
    """Test parsing of valid tag data from API response."""
    mock_response_data = {
        "tags": [
            {
                "name": "Temperature",
                "path": "Plant.Area1.Temperature",
                "dataType": "float",
                "description": "Temperature sensor",
            },
            {
                "name": "Pressure",
                "path": "Plant.Area1.Pressure",
                "dataType": "float",
                "description": "Pressure sensor",
            },
        ]
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

        mock_search_response = MagicMock()
        mock_search_response.json.return_value = mock_response_data
        mock_search_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = [mock_auth_response, mock_search_response]

            result = await search_tags.fn("Temp*")

            assert result["success"] is True
            assert result["count"] == 2
            assert len(result["tags"]) == 2
            assert result["tags"][0]["name"] == "Temperature"
            assert result["tags"][0]["path"] == "Plant.Area1.Temperature"
            assert result["tags"][0]["dataType"] == "float"
            assert result["tags"][0]["description"] == "Temperature sensor"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_tags_data_parsing_missing_fields():
    """Test parsing of tag data with missing optional fields."""
    mock_response_data = {
        "tags": [
            {
                "name": "Tag1",
                # Missing path, dataType, description
            }
        ]
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

        mock_search_response = MagicMock()
        mock_search_response.json.return_value = mock_response_data
        mock_search_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = [mock_auth_response, mock_search_response]

            result = await search_tags.fn("Tag1")

            assert result["success"] is True
            assert result["count"] == 1
            assert result["tags"][0]["name"] == "Tag1"
            assert result["tags"][0]["path"] == "Tag1"  # Fallback to name
            assert result["tags"][0]["dataType"] == "unknown"  # Default
            assert result["tags"][0]["description"] == ""  # Default


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_tags_data_parsing_empty_tags():
    """Test parsing of response with empty tags array."""
    mock_response_data = {"tags": []}

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

        mock_search_response = MagicMock()
        mock_search_response.json.return_value = mock_response_data
        mock_search_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = [mock_auth_response, mock_search_response]

            result = await search_tags.fn("NonExistent")

            assert result["success"] is True
            assert result["count"] == 0
            assert result["tags"] == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_tags_response_format_success():
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

        mock_search_response = MagicMock()
        mock_search_response.json.return_value = {"tags": []}
        mock_search_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = [mock_auth_response, mock_search_response]

            result = await search_tags.fn("Pattern")

            # Verify response structure
            assert "success" in result
            assert "tags" in result
            assert "count" in result
            assert "pattern" in result
            assert result["success"] is True
            assert isinstance(result["tags"], list)
            assert isinstance(result["count"], int)
            assert result["pattern"] == "Pattern"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_tags_response_format_error():
    """Test that error response has correct format."""
    result = await search_tags.fn("")

    # Verify error response structure
    assert "success" in result
    assert "error" in result
    assert "tags" in result
    assert "count" in result
    assert result["success"] is False
    assert isinstance(result["error"], str)
    assert result["tags"] == []
    assert result["count"] == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_tags_error_message_formatting():
    """Test that error messages are properly formatted."""
    # Test empty pattern error
    result = await search_tags.fn("")
    assert "empty" in result["error"].lower()

    # Test whitespace pattern error
    result = await search_tags.fn("   ")
    assert "empty" in result["error"].lower()
