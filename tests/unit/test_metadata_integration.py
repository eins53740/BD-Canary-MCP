"""Unit test verifying metadata integration within get_tag_path scoring."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict
from unittest.mock import AsyncMock

import pytest

from canary_mcp.server import get_tag_path


class MemoryCache:
    """Simple cache mock storing values in memory."""

    def __init__(self) -> None:
        self.store: Dict[str, Any] = {}

    def _generate_cache_key(self, namespace: str, tag: str, start_time: str | None = None, end_time: str | None = None) -> str:
        key_parts = [namespace, tag]
        if start_time:
            key_parts.append(start_time)
        if end_time:
            key_parts.append(end_time)
        return "::".join(key_parts)

    def get(self, key: str) -> Any:
        return self.store.get(key)

    def set(self, key: str, value: Any, category: str = "metadata", ttl: int | None = None) -> None:
        self.store[key] = value


@pytest.mark.unit
@pytest.mark.asyncio
async def test_metadata_description_influences_ranking(monkeypatch):
    """Metadata descriptions should affect the scoring outcome."""
    cache = MemoryCache()
    monkeypatch.setattr("canary_mcp.server.get_cache_store", lambda: cache)

    mock_search = AsyncMock(
        return_value={
            "success": True,
            "tags": [
                {
                    "name": "Section15Temp",
                    "path": "Plant.Kiln.Section15.Temp",
                    "dataType": "float",
                    "description": "",
                },
                {
                    "name": "Section15Vibe",
                    "path": "Plant.Kiln.Section15.Vibration",
                    "dataType": "float",
                    "description": "",
                },
            ],
            "count": 2,
            "pattern": "kiln vibration sensor",
            "cached": False,
        }
    )
    monkeypatch.setattr("canary_mcp.server.search_tags", SimpleNamespace(fn=mock_search))

    metadata_side_effect = [
        (
            {
                "name": "Section15Temp",
                "path": "Plant.Kiln.Section15.Temp",
                "description": "Temperature sensor for section 15",
                "dataType": "float",
            },
            False,
        ),
        (
            {
                "name": "Section15Vibe",
                "path": "Plant.Kiln.Section15.Vibration",
                "description": "Vibration monitoring sensor for kiln shell",
                "dataType": "float",
                "properties": {"category": "vibration"},
            },
            False,
        ),
    ]

    monkeypatch.setattr(
        "canary_mcp.server._get_tag_metadata_cached",
        AsyncMock(side_effect=metadata_side_effect),
    )

    result = await get_tag_path.fn("Need the kiln section 15 vibration sensor details")

    assert result["success"] is True
    assert result["most_likely_path"] == "Plant.Kiln.Section15.Vibration"
    assert result["candidates"][0]["matched_keywords"]["description"]
    assert result["confidence"] >= 0.8
    assert result["next_step"] == "return_path"
