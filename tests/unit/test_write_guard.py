"""Tests for the WRITE dataset guard helpers."""

import pytest

from canary_mcp.write_guard import (
    DEFAULT_ALLOWED_DATASETS,
    WriteDatasetError,
    get_allowed_datasets,
    validate_test_dataset,
)


@pytest.mark.unit
def test_validate_test_dataset_accepts_whitelisted_values():
    assert validate_test_dataset("Test/Maceira") == "Test/Maceira"
    assert validate_test_dataset("Test/Outao") == "Test/Outao"


@pytest.mark.unit
def test_validate_test_dataset_rejects_non_test_namespace():
    with pytest.raises(WriteDatasetError) as exc:
        validate_test_dataset("Prod/Maceira")
    assert "Test/*" in str(exc.value)


@pytest.mark.unit
def test_validate_test_dataset_rejects_unlisted_datasets(monkeypatch):
    monkeypatch.setenv("CANARY_WRITE_ALLOWED_DATASETS", "Test/Maceira")
    with pytest.raises(WriteDatasetError) as exc:
        validate_test_dataset("Test/Outao")
    assert "whitelisted" in str(exc.value)


@pytest.mark.unit
def test_get_allowed_datasets_defaults(monkeypatch):
    monkeypatch.delenv("CANARY_WRITE_ALLOWED_DATASETS", raising=False)
    assert get_allowed_datasets() == DEFAULT_ALLOWED_DATASETS
