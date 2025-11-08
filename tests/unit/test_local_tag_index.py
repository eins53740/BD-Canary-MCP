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


@pytest.mark.unit
def test_local_tag_index_respects_result_limits():
    """Metadata-only searches should honor the provided limit to keep responses bounded."""
    index = LocalTagIndex()
    limit = 7
    results = index.search(
        ["temperature"], description="any temperature tag", limit=limit
    )
    assert len(results) <= limit


@pytest.mark.unit
def test_get_local_tag_candidates_merges_vector_results(monkeypatch):
    """Vector retriever results should be appended when keyword search is empty."""
    from canary_mcp import tag_index

    class DummyRetriever:
        def search(self, text, *, limit):
            return [
                {
                    "path": "Test.Vector.Tag",
                    "description": text,
                    "unit": "degC",
                    "plant": "Secil",
                    "equipment": "Vector",
                    "score": 0.99,
                }
            ]

    monkeypatch.setattr(tag_index, "_get_vector_retriever", lambda: DummyRetriever())
    monkeypatch.setattr(tag_index, "_vector_search_enabled", lambda: True)
    monkeypatch.setattr(tag_index._LOCAL_TAG_INDEX, "search", lambda *a, **k: [])

    results = tag_index.get_local_tag_candidates(
        ["unlikelykeyword"],
        description="semantic kiln vibration query",
        limit=1,
    )

    assert results
    assert results[0]["path"] == "Test.Vector.Tag"
    assert results[0]["metadata"]["source"] == "vector-index"
