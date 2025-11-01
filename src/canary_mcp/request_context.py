"""Request context management for tracking request IDs across async operations.

This module provides request ID generation and tracking using Python's contextvars,
enabling correlation of log entries across async function calls within a single request.
"""

import contextvars
import uuid
from typing import Optional

# Context variable to store request-specific data
request_context: contextvars.ContextVar[dict] = contextvars.ContextVar(
    "request_context", default={}
)


def generate_request_id() -> str:
    """Generate a new unique request ID using UUID4.

    Returns:
        UUID4 string for request tracking
    """
    return str(uuid.uuid4())


def set_request_id(request_id: Optional[str] = None) -> str:
    """Set the request ID in the context.

    If no request_id is provided, generates a new one.

    Args:
        request_id: Optional existing request ID to use

    Returns:
        The request ID that was set
    """
    if request_id is None:
        request_id = generate_request_id()

    ctx = request_context.get().copy()
    ctx["request_id"] = request_id
    request_context.set(ctx)

    return request_id


def get_request_id() -> str:
    """Get the current request ID from context.

    Returns:
        Current request ID, or 'unknown' if not set
    """
    ctx = request_context.get()
    return ctx.get("request_id", "unknown")


def clear_request_context() -> None:
    """Clear the request context.

    Useful for cleanup between requests in testing.
    """
    request_context.set({})


def get_context_dict() -> dict:
    """Get the entire request context dictionary.

    Returns:
        Dictionary containing all context data
    """
    return request_context.get().copy()
