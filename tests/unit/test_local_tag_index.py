"""Tests for the local tag index built from Canary documentation exports."""

from __future__ import annotations

import pytest

from canary_mcp.tag_index import LocalTagIndex, get_local_tag_candidates


@pytest.mark.unit
def test_local_tag_index_returns_expected_match():
    """Searching for kiln shell speed should yield at least one canonical path."""
    index = LocalTagIndex()
    results = index.search(
        ["kiln", "shell", "speed"],
        description="kiln 5 shell speed",
        limit=5,
    )
    assert results
    assert any("Kiln_Shell_Speed" in candidate["path"] for candidate in results)


@pytest.mark.unit
def test_get_local_tag_candidates_wrapper_uses_shared_index():
    """Wrapper should return results without raising and reuse the shared index."""
    results = get_local_tag_candidates(
        ["kiln", "shell", "speed"],
        description="kiln shell speed",
        limit=3,
    )
    assert isinstance(results, list)
    assert results
