"""Integration tests validating caching behaviour of the get_tag_path tool."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict
from unittest.mock import AsyncMock

import pytest

from canary_mcp.server import get_tag_path


class MemoryCache:
    """In-memory cache to observe caching interactions without touching disk."""

    def __init__(self) -> None:
        self.store: Dict[str, Any] = {}

    def _generate_cache_key(self, namespace: str, tag: str, start_time: str | None = None, end_time: str | None = None) -> str:
        parts = [namespace, tag]
        if start_time:
            parts.append(start_time)
        if end_time:
            parts.append(end_time)
        return "::".join(parts)

    def get(self, key: str) -> Any:
        return self.store.get(key)

    def set(self, key: str, value: Any, category: str = "metadata", ttl: int | None = None) -> None:
        self.store[key] = value


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_tag_path_caching_and_bypass(monkeypatch):
    """Verify result caching, metadata caching, and bypass behavior."""
    cache = MemoryCache()
    monkeypatch.setattr("canary_mcp.server.get_cache_store", lambda: cache)

    search_mock = AsyncMock(
        return_value={
            "success": True,
            "tags": [
                {
                    "name": "KilnShellTemp",
                    "path": "Plant.Kiln.Section15.ShellTemp",
                    "dataType": "float",
                    "description": "",
                }
            ],
            "count": 1,
            "pattern": "kiln shell temperature",
            "cached": False,
        }
    )
    monkeypatch.setattr("canary_mcp.server.search_tags", SimpleNamespace(fn=search_mock))

    metadata_response = {
        "success": True,
        "metadata": {
            "name": "KilnShellTemp",
            "path": "Plant.Kiln.Section15.ShellTemp",
            "description": "Shell temperature sensor in section 15",
            "dataType": "float",
            "properties": {"unit": "C"},
        },
        "tag_path": "Plant.Kiln.Section15.ShellTemp",
    }

    metadata_mock = AsyncMock(return_value=metadata_response)
    monkeypatch.setattr("canary_mcp.server.get_tag_metadata", SimpleNamespace(fn=metadata_mock))

    # First invocation populates cache
    result1 = await get_tag_path.fn("Kiln shell temperature in section 15")

    assert result1["success"] is True
    assert result1["cached"] is False
    initial_search_calls = search_mock.await_count
    initial_metadata_calls = metadata_mock.await_count
    assert initial_search_calls > 0
    assert initial_metadata_calls > 0
    assert any("tag_metadata" in key for key in cache.store.keys())

    # Second invocation should hit cache and avoid downstream calls
    result2 = await get_tag_path.fn("Kiln shell temperature in section 15")

    assert result2["cached"] is True
    assert search_mock.await_count == initial_search_calls
    assert metadata_mock.await_count == initial_metadata_calls

    # Third invocation bypasses cache and triggers fresh lookups
    result3 = await get_tag_path.fn("Kiln shell temperature in section 15", bypass_cache=True)

    assert result3["cached"] is False
    assert search_mock.await_count > initial_search_calls
    assert metadata_mock.await_count > initial_metadata_calls
