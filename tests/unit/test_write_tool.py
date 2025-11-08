"""Unit tests for the write_test_dataset MCP tool."""

from __future__ import annotations

import pytest

from canary_mcp.server import write_test_dataset


def _set_common_env(monkeypatch):
    monkeypatch.setenv("CANARY_WRITER_ENABLED", "true")
    monkeypatch.setenv("CANARY_TESTER_ROLES", "tester")
    monkeypatch.setenv("CANARY_SAF_BASE_URL", "https://example.com/api/v1")


@pytest.mark.asyncio
async def test_write_tool_requires_tester_role(monkeypatch):
    """Non-tester roles should receive a permission error."""
    _set_common_env(monkeypatch)

    result = await write_test_dataset.fn(
        dataset="Test/Maceira",
        records=[
            {
                "tag": "Test/Maceira/MCP.Audit.Success",
                "value": 1,
                "timestamp": "2025-01-01T00:00:00Z",
            }
        ],
        original_prompt="Log success",
        role="analyst",
        dry_run=True,
    )

    assert result["success"] is False
    assert result["status"] == 403
    assert "authorized" in result["error"]


@pytest.mark.asyncio
async def test_write_tool_dry_run_returns_preview(monkeypatch):
    """Dry-run mode should validate and preview without calling Canary."""
    _set_common_env(monkeypatch)

    result = await write_test_dataset.fn(
        dataset="Test/Maceira",
        records=[
            {
                "tag": "Test/Maceira/MCP.Audit.Success",
                "value": 1,
                "timestamp": "2025-01-01T00:00:00Z",
            }
        ],
        original_prompt="Dry run this write",
        role="tester",
        dry_run=True,
    )

    assert result["success"] is True
    assert result["dry_run"] is True
    assert result["records_written"] == 0
    assert result["records"][0]["tag"].startswith("Test/Maceira")


@pytest.mark.asyncio
async def test_write_tool_dataset_validation(monkeypatch):
    """Datasets outside Test/* should be rejected."""
    _set_common_env(monkeypatch)

    result = await write_test_dataset.fn(
        dataset="Prod/Maceira",
        records=[
            {
                "tag": "Prod/Maceira/Should.Fail",
                "value": 5,
            }
        ],
        original_prompt="Should fail",
        role="tester",
        dry_run=True,
    )

    assert result["success"] is False
    assert result["status"] == 400
    assert "Dataset must live under the Test/*" in result["error"]


@pytest.mark.asyncio
async def test_write_tool_executes_http_call(monkeypatch):
    """Successful writes should call Canary SAF once and return API payload."""
    _set_common_env(monkeypatch)

    class DummyAuthClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get_valid_token(self) -> str:
            return "session-token"

    class DummyResponse:
        def __init__(self):
            self._json = {"status": "OK"}
            self.content = b'{"status": "OK"}'

        def raise_for_status(self):
            return None

        def json(self):
            return self._json

    class DummyHTTPClient:
        def __init__(self, *args, **kwargs):
            self.payload = None

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json):
            self.payload = json
            assert url.endswith("/manualEntryStoreData")
            return DummyResponse()

    monkeypatch.setattr("canary_mcp.server.CanaryAuthClient", lambda: DummyAuthClient())
    monkeypatch.setattr("canary_mcp.server.httpx.AsyncClient", DummyHTTPClient)

    result = await write_test_dataset.fn(
        dataset="Test/Maceira",
        records=[
            {
                "tag": "Test/Maceira/MCP.Audit.Success",
                "value": 1.0,
            }
        ],
        original_prompt="Record success flag",
        role="tester",
        dry_run=False,
    )

    assert result["success"] is True
    assert result["records_written"] == 1
    assert result["api_response"]["status"] == "OK"
