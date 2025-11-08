"""Unit tests for newly added Canary tools (get_aggregates, asset APIs, events)."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from canary_mcp.server import (
    browse_status,
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
async def test_get_asset_types_requires_views_base(monkeypatch):
    """Tool should fail when CANARY_VIEWS_BASE_URL is missing."""
    monkeypatch.delenv("CANARY_VIEWS_BASE_URL", raising=False)
    result = await get_asset_types.fn()
    assert result["success"] is False
    assert "CANARY_VIEWS_BASE_URL" in result["error"]


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


@pytest.mark.asyncio
async def test_browse_status_requires_base_url(monkeypatch):
    """browse_status should fail when the views base URL is missing."""
    monkeypatch.delenv("CANARY_VIEWS_BASE_URL", raising=False)
    result = await browse_status.fn()
    assert result["success"] is False
    assert result["status"] == 500


@pytest.mark.asyncio
async def test_browse_status_success(monkeypatch):
    """browse_status should call the API with the provided parameters."""
    _patch_auth(monkeypatch)
    captured_params: dict[str, Any] = {}

    async def fake_execute(tool_name, client, url, params=None, json=None):
        nonlocal captured_params
        captured_params = params or {}
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "nodes": [{"path": "Secil.Portugal"}],
            "tags": [],
            "nextPath": "Secil.Portugal.Kiln6",
            "status": "Good",
        }
        return mock_resp

    monkeypatch.setenv("CANARY_VIEWS_BASE_URL", "https://example.com")
    monkeypatch.setattr("canary_mcp.server.execute_tool_request", fake_execute)

    result = await browse_status.fn(
        path="Secil.Portugal",
        depth=2,
        include_tags=False,
        view="Views/Assets",
    )

    assert result["success"] is True
    assert result["nodes"][0]["path"] == "Secil.Portugal"
    assert captured_params["path"] == "Secil.Portugal"
    assert captured_params["depth"] == "2"
    assert captured_params["includeTags"] == "false"
    assert captured_params["views"] == "Views/Assets"
