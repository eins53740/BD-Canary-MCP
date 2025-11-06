"""Tests for the response size guard helper."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import pytest

from canary_mcp.response_guard import apply_response_size_limit


@dataclass
class StubLogger:
    """Minimal stub logger that records warning events."""

    warnings: list[tuple[str, dict]] = field(default_factory=list)

    def warning(self, event: str, **kwargs) -> None:
        self.warnings.append((event, kwargs))


def _measure_bytes(payload: dict) -> int:
    return len(json.dumps(payload).encode("utf-8"))


@pytest.mark.unit
def test_response_guard_no_truncation_when_under_limit():
    logger = StubLogger()
    payload = {"success": True, "values": [1, 2, 3], "message": "ok"}

    guarded, truncated = apply_response_size_limit(
        payload,
        request_id="req-123",
        logger=logger,
        limit_bytes=2048,
    )

    assert truncated is False
    assert guarded == payload
    assert logger.warnings == []


@pytest.mark.unit
def test_response_guard_truncates_large_payload():
    logger = StubLogger()
    # Craft payload exceeding the 4 KB test limit.
    values = ["x" * 256 for _ in range(200)]
    payload = {"success": True, "values": values, "meta": {"site": "Maceira"}}

    guarded, truncated = apply_response_size_limit(
        payload,
        request_id="req-999",
        logger=logger,
        limit_bytes=4096,
    )

    assert truncated is True
    assert guarded.get("truncated") is True
    assert "limit_bytes" in guarded
    assert guarded["limit_bytes"] == 4096
    assert "truncation_note" in guarded
    assert _measure_bytes(guarded) <= 4096

    assert logger.warnings
    event, details = logger.warnings[0]
    assert event == "response_truncated"
    assert details["request_id"] == "req-999"
    assert details["limit_bytes"] == 4096
