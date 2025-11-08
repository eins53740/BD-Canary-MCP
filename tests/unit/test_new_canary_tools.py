"""Unit tests for newly added Canary tools (get_aggregates, asset APIs, events)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from canary_mcp.server import (
    get_aggregates,
    get_asset_instances,
    get_asset_types,
    get_events_limit10,
)


def _patch_auth(monkeypatch):
    class DummyClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get_valid_token(self):
            return "token"

    monkeypatch.setenv("CANARY_VIEWS_BASE_URL", "https://example.com")
    monkeypatch.setattr("canary_mcp.server.CanaryAuthClient", lambda: DummyClient())


@pytest.mark.asyncio
async def test_get_aggregates_success(monkeypatch):
    """Should return aggregate list when API responds successfully."""
    _patch_auth(monkeypatch)
    mock_response = MagicMock()
    mock_response.json.return_value = {"aggregates": ["Average", "Minimum"]}
    mock_response.raise_for_status = MagicMock()
    monkeypatch.setattr(
        "canary_mcp.server.execute_tool_request",
        AsyncMock(return_value=mock_response),
    )

    result = await get_aggregates.fn()
    assert result["success"] is True
    assert result["count"] == 2


@pytest.mark.asyncio
async def test_get_asset_types_requires_view(monkeypatch):
    """Missing view (and env override) should return a 400 error."""
    monkeypatch.delenv("CANARY_ASSET_VIEW", raising=False)
    result = await get_asset_types.fn()
    assert result["success"] is False
    assert result["status"] == 400


@pytest.mark.asyncio
async def test_get_asset_instances_payload(monkeypatch):
    """Requests should include provided path and asset type."""
    monkeypatch.setenv("CANARY_ASSET_VIEW", "Views/MyAssets")
    _patch_auth(monkeypatch)

    captured_payload = {}

    async def fake_execute(tool_name, client, url, json=None, params=None):
        nonlocal captured_payload
        captured_payload = json or {}
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"assetInstances": [{"path": "foo"}]}
        return mock_resp

    monkeypatch.setattr("canary_mcp.server.execute_tool_request", fake_execute)

    result = await get_asset_instances.fn("Kiln", None, "Line1")
    assert result["success"] is True
    assert captured_payload["assetType"] == "Kiln"
    assert captured_payload["path"] == "Line1"


@pytest.mark.asyncio
async def test_get_events_limit_validation(monkeypatch):
    """Limit must be positive."""
    result = await get_events_limit10.fn(limit=0)
    assert result["success"] is False
    assert result["status"] == 400
