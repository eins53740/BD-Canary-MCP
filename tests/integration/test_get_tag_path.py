"""Integration tests covering the full get_tag_path workflow."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict, List
from unittest.mock import AsyncMock

import pytest

from canary_mcp.server import get_tag_path


class MemoryCache:
    """Shared cache for integration scenarios."""

    def __init__(self) -> None:
        self.store: Dict[str, Any] = {}

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


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_tag_path_end_to_end(monkeypatch):
    """Validate ranking, alternatives, and response structure."""
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
                },
                {
                    "name": "KilnShellPressure",
                    "path": "Plant.Kiln.Section15.ShellPressure",
                    "dataType": "float",
                    "description": "",
                },
                {
                    "name": "CoolingWaterTemp",
                    "path": "Plant.Kiln.Cooling.WaterTemp",
                    "dataType": "float",
                    "description": "",
                },
            ],
            "count": 3,
            "pattern": "kiln shell temperature",
            "cached": False,
        }
    )
    monkeypatch.setattr("canary_mcp.server.search_tags", SimpleNamespace(fn=search_mock))

    metadata_side_effect = [
        {
            "success": True,
            "metadata": {
                "name": "KilnShellTemp",
                "path": "Plant.Kiln.Section15.ShellTemp",
                "description": "Temperature sensor located on kiln shell section 15",
                "dataType": "float",
                "properties": {"unit": "C"},
            },
            "tag_path": "Plant.Kiln.Section15.ShellTemp",
        },
        {
            "success": True,
            "metadata": {
                "name": "KilnShellPressure",
                "path": "Plant.Kiln.Section15.ShellPressure",
                "description": "Pressure sensor located on kiln shell section 15",
                "dataType": "float",
                "properties": {"unit": "psi"},
            },
            "tag_path": "Plant.Kiln.Section15.ShellPressure",
        },
        {
            "success": True,
            "metadata": {
                "name": "CoolingWaterTemp",
                "path": "Plant.Kiln.Cooling.WaterTemp",
                "description": "Cooling water temperature sensor",
                "dataType": "float",
                "properties": {"unit": "C"},
            },
            "tag_path": "Plant.Kiln.Cooling.WaterTemp",
        },
    ]

    metadata_mock = AsyncMock(side_effect=metadata_side_effect)
    monkeypatch.setattr("canary_mcp.server.get_tag_metadata", SimpleNamespace(fn=metadata_mock))

    result = await get_tag_path.fn("Looking for kiln shell temperature sensor information")

    assert result["success"] is True
    assert result["most_likely_path"] == "Plant.Kiln.Section15.ShellTemp"
    assert len(result["candidates"]) == 3
    assert result["alternatives"] == [
        "Plant.Kiln.Section15.ShellPressure",
        "Plant.Kiln.Cooling.WaterTemp",
    ]
    assert result["candidates"][0]["matched_keywords"]["name"]
    assert "kiln" in result["keywords"]
    assert result["candidates"][0]["score"] >= result["candidates"][1]["score"]
    assert cache.store  # Response cached
