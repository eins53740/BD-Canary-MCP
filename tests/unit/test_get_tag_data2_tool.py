"""Unit tests for get_tag_data2 MCP tool."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from canary_mcp.server import GET_TAG_DATA2_HINT, get_tag_data2


def _common_env(monkeypatch):
    monkeypatch.setenv("CANARY_SAF_BASE_URL", "https://test.canary.com/api/v1")
    monkeypatch.setenv("CANARY_VIEWS_BASE_URL", "https://test.canary.com")
    monkeypatch.setenv("CANARY_API_TOKEN", "test-token")


@pytest.mark.asyncio
async def test_get_tag_data2_with_aggregates(monkeypatch):
    """Payload should include aggregates and maxSize when provided."""
    _common_env(monkeypatch)
    monkeypatch.setattr(
        "canary_mcp.server.search_tags",
        MagicMock(fn=AsyncMock(return_value={"success": True, "tags": []})),
    )

    mock_auth_response = MagicMock()
    mock_auth_response.json.return_value = {"sessionToken": "session-123"}
    mock_auth_response.raise_for_status = MagicMock()

    mock_data_response = MagicMock()
    mock_data_response.json.return_value = {"data": []}
    mock_data_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.side_effect = [mock_auth_response, mock_data_response]

        result = await get_tag_data2.fn(
            ["Tag1"],
            "2025-10-30T00:00:00Z",
            "2025-10-31T00:00:00Z",
            aggregate_name="TimeAverage2",
            aggregate_interval="00:05:00",
            max_size=5000,
        )

    # First post = auth, second = getTagData2 payload
    payload = mock_post.call_args_list[1].kwargs["json"]
    assert payload["aggregateName"] == "TimeAverage2"
    assert payload["aggregateInterval"] == "00:05:00"
    assert payload["maxSize"] == 5000
    assert result["success"] is True
    assert result["aggregate_name"] == "TimeAverage2"
    assert result["summary"]["total_samples"] == 0


@pytest.mark.asyncio
async def test_get_tag_data2_rejects_invalid_max_size(monkeypatch):
    """maxSize must be positive."""
    _common_env(monkeypatch)

    result = await get_tag_data2.fn(
        ["Tag1"], "2025-10-30T00:00:00Z", "2025-10-31T00:00:00Z", max_size=0
    )

    assert result["success"] is False
    assert result["status"] == 400
    assert "maxSize" in result["error"]
    assert result["hint"] == GET_TAG_DATA2_HINT
