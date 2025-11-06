"""Utilities for enforcing payload size limits on MCP tool responses."""

from __future__ import annotations

from typing import Any, Tuple

import json

DEFAULT_LIMIT_BYTES = 1_000_000

__all__ = ["DEFAULT_LIMIT_BYTES", "apply_response_size_limit"]


def _measure_size_bytes(payload: Any) -> int:
    """Return the UTF-8 byte length of the serialized payload."""
    serialized = json.dumps(payload, default=str, ensure_ascii=False)
    return len(serialized.encode("utf-8"))


def _build_truncated_payload(
    payload: Any,
    *,
    limit_bytes: int,
    request_id: str | None,
    original_size: int,
) -> dict[str, Any]:
    """Return a compact payload that signals truncation and provides context."""
    serialized = json.dumps(payload, default=str, ensure_ascii=False)
    preview_length = min(len(serialized), max(256, limit_bytes // 4))
    preview = serialized[:preview_length]

    truncated_payload: dict[str, Any] = {
        "truncated": True,
        "limit_bytes": limit_bytes,
        "original_size_bytes": original_size,
        "truncation_note": (
            "Response truncated to comply with the 1 MB payload guardrail. "
            "Refine the query (narrow time window, fewer tags, or apply filters) and try again."
        ),
        "preview": preview,
    }

    if isinstance(payload, dict):
        if "success" in payload:
            truncated_payload["success"] = payload["success"]
        if "count" in payload:
            truncated_payload["approximate_count"] = payload["count"]
        if "pattern" in payload:
            truncated_payload["pattern"] = payload["pattern"]

    if request_id:
        truncated_payload["request_id"] = request_id

    return truncated_payload


def apply_response_size_limit(
    payload: Any,
    *,
    request_id: str | None = None,
    logger: Any | None = None,
    limit_bytes: int = DEFAULT_LIMIT_BYTES,
) -> Tuple[Any, bool]:
    """Ensure payloads stay within the configured byte limit."""
    size_bytes = _measure_size_bytes(payload)
    if size_bytes <= limit_bytes:
        return payload, False

    truncated_payload = _build_truncated_payload(
        payload,
        limit_bytes=limit_bytes,
        request_id=request_id,
        original_size=size_bytes,
    )

    if logger is not None:
        logger.warning(
            "response_truncated",
            request_id=request_id,
            size_bytes=size_bytes,
            limit_bytes=limit_bytes,
        )

    return truncated_payload, True
