"""Story 4.5 success validation coverage."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from canary_mcp.server import get_tag_path, read_timeseries


class MemoryCache:
    """Minimal in-memory cache to exercise caching behaviour deterministically."""

    def __init__(self) -> None:
        self.store: dict[str, dict[str, object]] = {}

    def _generate_cache_key(self, namespace: str, tag: str, *_args) -> str:
        return f"{namespace}::{tag}"

    def get(self, key: str):
        return self.store.get(key)

    def set(self, key: str, value, category: str = "metadata", ttl=None):
        self.store[key] = value


class DummyResponse:
    """Lightweight stand-in for an httpx.Response object."""

    def __init__(self, payload: dict[str, object]):
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        return None


class DummyAuthClient:
    """Async context manager that mimics CanaryAuthClient without network."""

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get_valid_token(self) -> str:
        return "test-token"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_timeseries_multi_tag_correlation_summary(monkeypatch):
    """read_timeseries should provide multi-tag summaries with range + site hints."""
    monkeypatch.setenv("CANARY_VIEWS_BASE_URL", "https://example.canary")
    monkeypatch.setattr("canary_mcp.server.CanaryAuthClient", lambda: DummyAuthClient())

    async def fake_resolve(tag_identifiers, *, include_original=True):
        resolved = {tag: f"Secil.Portugal.{tag}" for tag in tag_identifiers}
        resolved_list = list(resolved.values())
        lookup = (
            list(tag_identifiers) + resolved_list if include_original else resolved_list
        )
        return lookup, resolved

    monkeypatch.setattr("canary_mcp.server._resolve_tag_identifiers", fake_resolve)

    payload = {
        "data": {
            "Secil.Portugal.Kiln6.ShellTemp": [
                {
                    "timestamp": "2025-10-30T10:00:00Z",
                    "value": 832.1,
                    "quality": "good",
                },
                {
                    "timestamp": "2025-10-30T10:05:00Z",
                    "value": 833.4,
                    "quality": "good",
                },
            ],
            "Secil.Portugal.Kiln6.ShellPressure": [
                {"timestamp": "2025-10-30T10:00:00Z", "value": 3.2, "quality": "good"}
            ],
        }
    }

    async def fake_execute_tool_request(*_args, **_kwargs):
        return DummyResponse(payload)

    monkeypatch.setattr(
        "canary_mcp.server.execute_tool_request", fake_execute_tool_request
    )
    monkeypatch.setattr(
        "canary_mcp.server.get_last_known_values",
        SimpleNamespace(fn=AsyncMock(return_value={"success": False})),
    )

    result = await read_timeseries.fn(
        ["Kiln6.ShellTemp", "Kiln6.ShellPressure"],
        "2025-10-30T10:00:00Z",
        "2025-10-30T11:00:00Z",
    )

    assert result["success"] is True
    assert result["count"] == 3
    assert result["resolved_tag_names"] == {
        "Kiln6.ShellTemp": "Secil.Portugal.Kiln6.ShellTemp",
        "Kiln6.ShellPressure": "Secil.Portugal.Kiln6.ShellPressure",
    }
    summary = result["summary"]
    assert summary["total_samples"] == 3
    assert summary["samples_per_tag"]["Secil.Portugal.Kiln6.ShellTemp"] == 2
    assert summary["samples_per_tag"]["Secil.Portugal.Kiln6.ShellPressure"] == 1
    assert summary["range"]["start"] == "2025-10-30T10:00:00Z"
    assert summary["range"]["end"] == "2025-10-30T11:00:00Z"
    assert summary["site_hint"] == "Secil.Portugal"
    assert summary["requested_tags"] == ["Kiln6.ShellTemp", "Kiln6.ShellPressure"]


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_tag_lookup_batch_accuracy_and_clarifications(monkeypatch):
    """200-query batch should exceed 90% accuracy and ask clarifying questions when unsure."""
    cache = MemoryCache()
    monkeypatch.setattr("canary_mcp.server.get_cache_store", lambda: cache)
    monkeypatch.setattr(
        "canary_mcp.server.get_local_tag_candidates", lambda *a, **k: []
    )

    async def fake_search(pattern, bypass_cache=False):
        return {
            "success": True,
            "tags": [
                {
                    "name": "KilnShellTemp",
                    "path": "Secil.Portugal.Kiln6.Section15.ShellTemp",
                    "dataType": "float",
                    "description": "Kiln 6 shell temperature section 15",
                    "units": "degC",
                }
            ],
            "count": 1,
            "pattern": pattern,
            "cached": False,
        }

    search_mock = AsyncMock(side_effect=fake_search)
    monkeypatch.setattr(
        "canary_mcp.server.search_tags", SimpleNamespace(fn=search_mock)
    )
    metadata_mock = AsyncMock(
        return_value=(
            {
                "name": "KilnShellTemp",
                "path": "Secil.Portugal.Kiln6.Section15.ShellTemp",
                "description": "Kiln 6 shell temperature section 15",
                "dataType": "float",
                "units": "degC",
            },
            False,
        )
    )
    monkeypatch.setattr("canary_mcp.server._get_tag_metadata_cached", metadata_mock)

    confidence_plan = ["high"] * 182 + ["low"] * 18
    plan_iter = iter(confidence_plan)

    def fake_compute_confidence(candidates):
        try:
            label = next(plan_iter)
        except StopIteration as exc:
            raise AssertionError("Confidence plan exhausted") from exc
        return (0.92, "high") if label == "high" else (0.5, "low")

    monkeypatch.setattr(
        "canary_mcp.server._compute_confidence", fake_compute_confidence
    )

    descriptions = [
        f"Kiln 6 shell temperature section {i % 20} window {i}"
        for i in range(len(confidence_plan))
    ]

    successes = 0
    clarifications = 0
    clarification_prompts: set[str] = set()

    for description in descriptions:
        result = await get_tag_path.fn(description, bypass_cache=True)
        if result["success"]:
            successes += 1
            assert result["confidence"] >= 0.7
            assert (
                result["most_likely_path"] == "Secil.Portugal.Kiln6.Section15.ShellTemp"
            )
        else:
            clarifications += 1
            assert result["next_step"] == "clarify"
            assert result["clarifying_question"]
            clarification_prompts.add(result["clarifying_question"])

    assert successes == 182
    assert clarifications == 18
    assert successes / len(descriptions) >= 0.9
    assert clarification_prompts  # Coverage that clarification guidance was surfaced

    with pytest.raises(StopIteration):
        next(plan_iter)
