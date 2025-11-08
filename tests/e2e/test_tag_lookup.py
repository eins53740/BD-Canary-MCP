"""End-to-end style tests for the tag lookup workflow."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from canary_mcp.server import get_tag_path


class MemoryCache:
    def __init__(self) -> None:
        self.store = {}

    def _generate_cache_key(self, namespace: str, tag: str, *_args) -> str:
        return f"{namespace}::{tag}"

    def get(self, key: str):
        return self.store.get(key)

    def set(self, key: str, value, category: str = "metadata", ttl=None):
        self.store[key] = value


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_tag_lookup_high_confidence(monkeypatch):
    """Workflow should produce a confident match and allow next-step automation."""
    cache = MemoryCache()
    monkeypatch.setattr("canary_mcp.server.get_cache_store", lambda: cache)
    monkeypatch.setattr("canary_mcp.server.get_local_tag_candidates", lambda *a, **k: [])

    search_mock = AsyncMock(
        return_value={
            "success": True,
            "tags": [
                {
                    "name": "KilnShellTemp",
                    "path": "Secil.Portugal.Kiln6.ShellTemp",
                    "dataType": "float",
                    "description": "Kiln 6 shell temperature section 15",
                }
            ],
            "count": 1,
            "pattern": "kiln shell temperature",
            "cached": False,
        }
    )
    monkeypatch.setattr("canary_mcp.server.search_tags", SimpleNamespace(fn=search_mock))
    monkeypatch.setattr(
        "canary_mcp.server._get_tag_metadata_cached",
        AsyncMock(
            return_value=(
                {
                    "name": "KilnShellTemp",
                    "path": "Secil.Portugal.Kiln6.ShellTemp",
                    "description": "Kiln 6 shell temperature section 15",
                    "dataType": "float",
                    "units": "degC",
                },
                False,
            )
        ),
    )

    result = await get_tag_path.fn("Find kiln 6 shell temperature in section 15")

    assert result["success"] is True
    assert result["confidence"] >= 0.8
    assert result["confidence_label"] == "high"
    assert result["next_step"] == "return_path"
    assert result["clarifying_question"] is None


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_tag_lookup_low_confidence_prompts_for_clarification(monkeypatch):
    """Low confidence responses should ask clarifying questions instead of guessing."""
    cache = MemoryCache()
    monkeypatch.setattr("canary_mcp.server.get_cache_store", lambda: cache)
    monkeypatch.setattr("canary_mcp.server.get_local_tag_candidates", lambda *a, **k: [])

    search_mock = AsyncMock(
        return_value={
            "success": True,
            "tags": [
                {
                    "name": "GenericTemp",
                    "path": "Secil.Portugal.Generic.Temp",
                    "dataType": "float",
                    "description": "Generic temperature",
                }
            ],
            "count": 1,
            "pattern": "temperature",
            "cached": False,
        }
    )
    monkeypatch.setattr("canary_mcp.server.search_tags", SimpleNamespace(fn=search_mock))
    monkeypatch.setattr(
        "canary_mcp.server._get_tag_metadata_cached",
        AsyncMock(
            return_value=(
                {
                    "name": "GenericTemp",
                    "path": "Secil.Portugal.Generic.Temp",
                    "description": "Generic temperature tag",
                    "dataType": "float",
                },
                False,
            )
        ),
    )
    # Force low confidence outcome to exercise the clarifying path.
    monkeypatch.setattr("canary_mcp.server._compute_confidence", lambda *_a, **_k: (0.5, "low"))

    result = await get_tag_path.fn("temperature")

    assert result["success"] is False
    assert result["next_step"] == "clarify"
    assert result["clarifying_question"]
    assert result["confidence_label"] == "low"
