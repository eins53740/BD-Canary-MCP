"""Unit tests covering the foundational behaviour of the get_tag_path tool."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, Dict, List
from unittest.mock import AsyncMock

import pytest

from canary_mcp.server import extract_keywords, get_tag_path


@dataclass
class InMemoryCache:
    """Minimal in-memory cache implementation for unit tests."""

    store: Dict[str, Any] = field(default_factory=dict)

    def _generate_cache_key(
        self,
        namespace: str,
        tag: str,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> str:
        parts: List[str] = [namespace, tag]
        if start_time:
            parts.append(start_time)
        if end_time:
            parts.append(end_time)
        return "::".join(parts)

    def get(self, key: str) -> Any:
        return self.store.get(key)

    def set(self, key: str, value: Any, category: str = "metadata", ttl: int | None = None) -> None:
        self.store[key] = value


@pytest.mark.unit
def test_extract_keywords_filters_stop_words():
    """Ensure keyword extraction removes stop words and lowercases tokens."""
    keywords = extract_keywords("Get the average Kiln Shell Temperature tag")
    assert keywords == ["kiln", "shell", "temperature"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_tag_path_returns_candidates(monkeypatch):
    """The tool should return a ranked candidate list when search yields matches."""
    memory_cache = InMemoryCache()
    monkeypatch.setattr("canary_mcp.server.get_cache_store", lambda: memory_cache)

    mock_search = AsyncMock(
        return_value={
            "success": True,
            "tags": [
                {
                    "name": "KilnShellTemp",
                    "path": "Plant.Kiln.Section15.ShellTemp",
                    "dataType": "float",
                    "description": "Shell temperature sensor",
                }
            ],
            "count": 1,
            "pattern": "kiln shell temperature",
            "cached": False,
        }
    )
    monkeypatch.setattr("canary_mcp.server.search_tags", SimpleNamespace(fn=mock_search))

    metadata_payload = (
        {
            "name": "KilnShellTemp",
            "path": "Plant.Kiln.Section15.ShellTemp",
            "description": "Shell temperature sensor in section 15",
            "dataType": "float",
        },
        False,
    )
    monkeypatch.setattr(
        "canary_mcp.server._get_tag_metadata_cached",
        AsyncMock(return_value=metadata_payload),
    )

    result = await get_tag_path.fn("Find the kiln shell temperature in section 15")

    assert result["success"] is True
    assert result["most_likely_path"] == "Plant.Kiln.Section15.ShellTemp"
    assert result["keywords"] == ["kiln", "shell", "temperature", "section", "15"]
    assert len(result["candidates"]) == 1
    assert result["candidates"][0]["score"] > 0
    assert memory_cache.store  # Final result should be cached


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_tag_path_validates_description(monkeypatch):
    """Empty descriptions should return an error without invoking downstream calls."""
    memory_cache = InMemoryCache()
    monkeypatch.setattr("canary_mcp.server.get_cache_store", lambda: memory_cache)

    # Ensure search_tags is not called
    mock_search = AsyncMock()
    monkeypatch.setattr("canary_mcp.server.search_tags", SimpleNamespace(fn=mock_search))
    monkeypatch.setattr(
        "canary_mcp.server._get_tag_metadata_cached",
        AsyncMock(),
    )

    result = await get_tag_path.fn("   ")

    assert result["success"] is False
    assert "empty" in result["error"].lower()
    mock_search.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_tag_path_handles_no_matches(monkeypatch):
    """When no matches are found the response should indicate failure."""
    memory_cache = InMemoryCache()
    monkeypatch.setattr("canary_mcp.server.get_cache_store", lambda: memory_cache)

    search_mock = AsyncMock(
        return_value={
            "success": True,
            "tags": [],
            "count": 0,
            "pattern": "unknown",
            "cached": False,
        }
    )
    monkeypatch.setattr("canary_mcp.server.search_tags", SimpleNamespace(fn=search_mock))
    monkeypatch.setattr(
        "canary_mcp.server._get_tag_metadata_cached",
        AsyncMock(),
    )

    result = await get_tag_path.fn("Unrecognized measurement phrase")

    assert result["success"] is False
    assert result["most_likely_path"] is None
    assert result["candidates"] == []
    assert "no tags" in result["error"].lower()
