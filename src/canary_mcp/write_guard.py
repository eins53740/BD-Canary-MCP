"""Helpers that enforce WRITE-tool safety constraints."""

from __future__ import annotations

import os
from typing import Iterable, Tuple

DEFAULT_ALLOWED_DATASETS: Tuple[str, ...] = ("Test/Maceira", "Test/Outao")


class WriteDatasetError(ValueError):
    """Raised when a dataset violates the Test/* policy."""


def _parse_allowed_datasets(raw: str | None) -> Tuple[str, ...]:
    if not raw:
        return DEFAULT_ALLOWED_DATASETS
    candidates = tuple(item.strip() for item in raw.split(",") if item.strip())
    return candidates or DEFAULT_ALLOWED_DATASETS


def get_allowed_datasets() -> Tuple[str, ...]:
    """Return the list of datasets authorized for WRITE operations."""
    env_value = os.getenv("CANARY_WRITE_ALLOWED_DATASETS")
    return _parse_allowed_datasets(env_value)


def validate_test_dataset(dataset: str) -> str:
    """
    Ensure the WRITE dataset respects the Test/* policy and whitelist.

    Args:
        dataset: Canary dataset name (e.g., "Test/Maceira")

    Returns:
        The normalized dataset string

    Raises:
        WriteDatasetError: if the dataset is empty or outside the allowed scope.
    """
    if dataset is None:
        raise WriteDatasetError("Dataset cannot be empty.")

    normalized = dataset.strip()
    if not normalized:
        raise WriteDatasetError("Dataset cannot be empty.")

    if not normalized.startswith("Test/"):
        raise WriteDatasetError(
            "Dataset must live under the Test/* namespace (e.g., Test/Maceira)."
        )

    allowed = get_allowed_datasets()
    if allowed and normalized not in allowed:
        raise WriteDatasetError(
            f"Dataset '{normalized}' is not whitelisted. Allowed datasets: {', '.join(allowed)}"
        )

    return normalized


__all__ = ["validate_test_dataset", "get_allowed_datasets", "WriteDatasetError"]
