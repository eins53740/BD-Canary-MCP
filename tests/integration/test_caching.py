"""
Integration tests for caching layer.

Story 2.2: Caching Layer Implementation
Tests cache hit/miss behavior, TTL, LRU eviction, and cache management.
"""

import tempfile
import time
from pathlib import Path

import pytest

from canary_mcp.cache import CacheConfig, CacheStore


@pytest.fixture
def temp_cache_dir():
    """Create temporary cache directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def cache_config(temp_cache_dir):
    """Create test cache configuration."""
    config = CacheConfig()
    config.cache_dir = temp_cache_dir
    config.cache_db = temp_cache_dir / "test_cache.db"
    config.metadata_ttl = 2  # Short TTL for testing
    config.timeseries_ttl = 1
    config.max_cache_size_bytes = 1024 * 100  # 100KB for testing eviction
    return config


@pytest.fixture
def cache_store(cache_config):
    """Create test cache store."""
    store = CacheStore(cache_config)
    yield store
    # Cleanup
    if cache_config.cache_db.exists():
        cache_config.cache_db.unlink()


@pytest.mark.integration
def test_cache_basic_set_get(cache_store):
    """Test basic cache set and get operations."""
    # Set a value
    test_data = {"result": "test_value", "count": 42}
    cache_store.set("test_key", test_data, ttl=10)

    # Get the value
    result = cache_store.get("test_key")
    assert result is not None
    assert result["result"] == "test_value"
    assert result["count"] == 42


@pytest.mark.integration
def test_cache_miss(cache_store):
    """Test cache miss returns None."""
    result = cache_store.get("nonexistent_key")
    assert result is None


@pytest.mark.integration
def test_cache_expiration(cache_store):
    """Test that cached entries expire after TTL."""
    # Set with short TTL
    cache_store.set("expiring_key", {"data": "test"}, ttl=1)

    # Should exist immediately
    result = cache_store.get("expiring_key")
    assert result is not None

    # Wait for expiration
    time.sleep(1.5)

    # Should be expired
    result = cache_store.get("expiring_key")
    assert result is None


@pytest.mark.integration
def test_cache_key_generation(cache_store):
    """Test cache key generation is consistent."""
    key1 = cache_store._generate_cache_key(
        "namespace", "tag1", "2024-01-01", "2024-01-02"
    )
    key2 = cache_store._generate_cache_key(
        "namespace", "tag1", "2024-01-01", "2024-01-02"
    )

    # Same parameters should generate same key
    assert key1 == key2

    # Different parameters should generate different keys
    key3 = cache_store._generate_cache_key(
        "namespace", "tag2", "2024-01-01", "2024-01-02"
    )
    assert key1 != key3


@pytest.mark.integration
def test_cache_hit_miss_statistics(cache_store):
    """Test that cache tracks hits and misses."""
    # Initial stats
    stats = cache_store.get_stats()
    initial_hits = stats["cache_hits"]
    initial_misses = stats["cache_misses"]

    # Set a value
    cache_store.set("stats_key", {"data": "test"})

    # Cache miss
    cache_store.get("nonexistent")

    # Cache hit
    cache_store.get("stats_key")

    # Check stats
    stats = cache_store.get_stats()
    assert stats["cache_misses"] == initial_misses + 1
    assert stats["cache_hits"] == initial_hits + 1


@pytest.mark.integration
def test_cache_access_count_tracking(cache_store):
    """Test that access counts are tracked."""
    # Set a value
    cache_store.set("access_key", {"data": "test"})

    # Access it multiple times
    for _ in range(5):
        cache_store.get("access_key")

    # Check stats
    stats = cache_store.get_stats()
    assert stats["total_accesses"] >= 5


@pytest.mark.integration
def test_cache_size_tracking(cache_store):
    """Test that cache size is tracked correctly."""
    # Set some data
    large_data = {"data": "x" * 1000}  # ~1KB
    cache_store.set("size_key", large_data)

    # Check stats
    stats = cache_store.get_stats()
    assert stats["total_size_bytes"] > 1000
    assert stats["entry_count"] == 1


@pytest.mark.integration
def test_cache_lru_eviction(cache_store):
    """Test that LRU eviction works when cache is full."""
    # Fill cache with data
    for i in range(150):  # More than 100KB
        large_data = {"data": "x" * 1000}  # ~1KB each
        cache_store.set(f"evict_key_{i}", large_data)

    # Check that some entries were evicted
    stats = cache_store.get_stats()
    assert stats["evictions"] > 0

    # Check that total size is under limit
    assert stats["total_size_bytes"] <= cache_store.config.max_cache_size_bytes


@pytest.mark.integration
def test_cache_invalidate_all(cache_store):
    """Test invalidating all cache entries."""
    # Add multiple entries
    for i in range(5):
        cache_store.set(f"inv_key_{i}", {"index": i})

    # Verify entries exist
    assert cache_store.get("inv_key_0") is not None

    # Invalidate all
    count = cache_store.invalidate()
    assert count == 5

    # Verify entries are gone
    assert cache_store.get("inv_key_0") is None


@pytest.mark.integration
def test_cache_invalidate_pattern(cache_store):
    """Test invalidating cache entries by pattern."""
    # Add entries with different prefixes
    cache_store.set("search:query1", {"result": 1})
    cache_store.set("search:query2", {"result": 2})
    cache_store.set("metadata:tag1", {"result": 3})

    # Invalidate only search entries
    _ = cache_store.invalidate("search:%")

    # Check that search entries are gone but metadata remains
    assert cache_store.get("search:query1") is None
    assert cache_store.get("search:query2") is None
    assert cache_store.get("metadata:tag1") is not None


@pytest.mark.integration
def test_cache_cleanup_expired(cache_store):
    """Test cleanup of expired entries."""
    # Add entries with different TTLs
    cache_store.set("short_ttl", {"data": 1}, ttl=1)
    cache_store.set("long_ttl", {"data": 2}, ttl=100)

    # Wait for short TTL to expire
    time.sleep(1.5)

    # Cleanup expired
    count = cache_store.cleanup_expired()
    assert count >= 1

    # Verify short TTL is gone, long TTL remains
    assert cache_store.get("short_ttl") is None
    assert cache_store.get("long_ttl") is not None


@pytest.mark.integration
def test_cache_category_ttl(cache_store):
    """Test that different categories use different TTLs."""
    # Set metadata (should use metadata_ttl = 2s)
    cache_store.set("meta_key", {"data": "meta"}, category="metadata")

    # Set timeseries (should use timeseries_ttl = 1s)
    cache_store.set("ts_key", {"data": "ts"}, category="timeseries")

    # Wait for timeseries TTL to expire
    time.sleep(1.5)

    # Timeseries should be expired, metadata should still be valid
    assert cache_store.get("ts_key") is None
    assert cache_store.get("meta_key") is not None


@pytest.mark.integration
def test_cache_json_serialization(cache_store):
    """Test that complex data structures are serialized correctly."""
    complex_data = {
        "nested": {
            "list": [1, 2, 3],
            "dict": {"key": "value"},
        },
        "number": 42,
        "string": "test",
        "boolean": True,
        "null": None,
    }

    cache_store.set("complex_key", complex_data)
    result = cache_store.get("complex_key")

    assert result == complex_data


@pytest.mark.integration
def test_cache_concurrent_access(cache_store):
    """Test that cache handles concurrent access safely."""
    import concurrent.futures

    def worker(worker_id):
        # Each worker sets and gets its own key
        key = f"concurrent_key_{worker_id}"
        data = {"worker": worker_id}
        cache_store.set(key, data)
        result = cache_store.get(key)
        return result == data

    # Run 10 workers concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(worker, i) for i in range(10)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    # All workers should succeed
    assert all(results)


@pytest.mark.integration
def test_cache_hit_rate_calculation(cache_store):
    """Test that hit rate is calculated correctly."""
    # Clear cache
    cache_store.invalidate()

    # 7 hits, 3 misses = 70% hit rate
    for i in range(10):
        if i < 7:
            cache_store.set(f"hit_key_{i}", {"data": i})

    for i in range(10):
        cache_store.get(f"hit_key_{i}")

    stats = cache_store.get_stats()
    hit_rate = stats["hit_rate_percent"]

    # Should be 70% (7 hits out of 10 requests)
    assert 65 <= hit_rate <= 75  # Allow some tolerance


@pytest.mark.integration
def test_cache_update_existing_entry(cache_store):
    """Test that updating an existing entry works correctly."""
    # Set initial value
    cache_store.set("update_key", {"version": 1})

    # Update with new value
    cache_store.set("update_key", {"version": 2})

    # Should get updated value
    result = cache_store.get("update_key")
    assert result["version"] == 2


@pytest.mark.integration
def test_cache_persistence(cache_config, temp_cache_dir):
    """Test that cache persists across store instances."""
    # Create first store and add data
    store1 = CacheStore(cache_config)
    store1.set("persist_key", {"data": "persistent"}, ttl=100)

    # Close and create new store
    del store1
    store2 = CacheStore(cache_config)

    # Should still be able to get the data
    result = store2.get("persist_key")
    assert result is not None
    assert result["data"] == "persistent"
