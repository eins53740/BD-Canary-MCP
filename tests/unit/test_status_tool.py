"""Unit tests for MCP server status tools (ping, mcp_status)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from freezegun import freeze_time

from canary_mcp.server import mcp_status, ping


def test_ping():
    """Should return the basic pong message."""
    result = ping.fn()
    assert result == "pong - Canary MCP Server is running!"


@pytest.mark.asyncio
@freeze_time("2025-11-10 12:00:00")
async def test_mcp_status_success(monkeypatch):
    """Should return a detailed status message on success."""
    # Mock weather API call
    mock_weather_response = MagicMock()
    mock_weather_response.json.return_value = {
        "current_condition": [
            {
                "temp_C": "15",
                "FeelsLikeC": "14",
                "weatherDesc": [{"value": "Sunny"}],
            }
        ]
    }
    mock_weather_response.raise_for_status = MagicMock()

    mock_async_client = MagicMock()
    mock_async_client.__aenter__.return_value.get.return_value = mock_weather_response
    monkeypatch.setattr(
        "canary_mcp.server.httpx.AsyncClient", lambda timeout: mock_async_client
    )

    # Mock git subprocess call
    mock_process = AsyncMock()
    mock_process.communicate.return_value = (b"2025-11-10 11:55:00 +0000", b"")
    mock_process.returncode = 0
    monkeypatch.setattr(
        "canary_mcp.server.asyncio.create_subprocess_exec",
        AsyncMock(return_value=mock_process),
    )

    # Mock logging
    mock_log = MagicMock()
    monkeypatch.setattr("canary_mcp.server.log", mock_log)

    result = await mcp_status.fn()

    assert "Secil Canary MCP is up and running" in result
    assert "Current time at Maceira site: 2025-11-10 12:00:00" in result
    assert "Current weather in Lisbon: Sunny, 15°C (feels like 14°C)" in result
    assert "Last project update: 2025-11-10 11:55:00 +0000" in result
    assert "By BD to the world - 2025 (c)." in result


@pytest.mark.asyncio
async def test_mcp_status_weather_fails(monkeypatch):
    """Should handle weather API failure gracefully."""
    # Mock weather API to raise an exception
    mock_async_client = MagicMock()
    mock_async_client.__aenter__.return_value.get.side_effect = Exception(
        "Network Error"
    )
    monkeypatch.setattr(
        "canary_mcp.server.httpx.AsyncClient", lambda timeout: mock_async_client
    )

    # Mock git subprocess call
    mock_process = AsyncMock()
    mock_process.communicate.return_value = (b"2025-11-10 11:55:00 +0000", b"")
    mock_process.returncode = 0
    monkeypatch.setattr(
        "canary_mcp.server.asyncio.create_subprocess_exec",
        AsyncMock(return_value=mock_process),
    )

    # Mock logging
    mock_log = MagicMock()
    monkeypatch.setattr("canary_mcp.server.log", mock_log)

    result = await mcp_status.fn()

    assert "Weather data currently unavailable" in result
    assert "Last project update: 2025-11-10 11:55:00 +0000" in result
    mock_log.warning.assert_called_with(
        "mcp_status_weather_error", error="Network Error"
    )


@pytest.mark.asyncio
async def test_mcp_status_git_fails(monkeypatch):
    """Should handle git command failure gracefully."""
    # Mock weather API call
    mock_weather_response = MagicMock()
    mock_weather_response.json.return_value = {
        "current_condition": [
            {
                "temp_C": "15",
                "FeelsLikeC": "14",
                "weatherDesc": [{"value": "Sunny"}],
            }
        ]
    }
    mock_weather_response.raise_for_status = MagicMock()
    mock_async_client = MagicMock()
    mock_async_client.__aenter__.return_value.get.return_value = mock_weather_response
    monkeypatch.setattr(
        "canary_mcp.server.httpx.AsyncClient", lambda timeout: mock_async_client
    )

    # Mock git subprocess to fail
    mock_process = AsyncMock()
    mock_process.communicate.return_value = (b"", b"git error")
    mock_process.returncode = 1
    monkeypatch.setattr(
        "canary_mcp.server.asyncio.create_subprocess_exec",
        AsyncMock(return_value=mock_process),
    )

    # Mock logging
    mock_log = MagicMock()
    monkeypatch.setattr("canary_mcp.server.log", mock_log)

    result = await mcp_status.fn()

    assert "Could not determine last update" in result
    assert "Current weather in Lisbon: Sunny, 15°C (feels like 14°C)" in result
    mock_log.warning.assert_called_with("mcp_status_git_log_error", error="git error")
