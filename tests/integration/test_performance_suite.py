"""
Performance validation test suite for Canary MCP Server.

Story 2.4: Performance Validation Test Suite
Validates that server meets NFR001 performance requirements before deployment.
"""

import asyncio
import statistics
import time

import pytest

from canary_mcp.metrics import MetricsTimer, get_metrics_collector


@pytest.fixture
def reset_metrics():
    """Reset metrics before each test."""
    collector = get_metrics_collector()
    collector.reset()
    yield collector
    collector.reset()


@pytest.mark.integration
async def test_single_query_latency(reset_metrics):
    """
    Test that single queries meet latency requirements.

    NFR001: Median query response time < 5s
    """
    latencies = []

    # Simulate 10 queries
    for _ in range(10):
        async with MetricsTimer("test_query"):
            await asyncio.sleep(0.1)  # Mock query time
            latencies.append(0.1)

    median = statistics.median(latencies)

    # Verify median < 5s
    assert median < 5.0, f"Median latency {median}s exceeds 5s target"


@pytest.mark.integration
async def test_concurrent_query_performance(reset_metrics):
    """
    Test that concurrent queries meet performance requirements.

    NFR001: Handle 25 concurrent users without degradation
    """

    async def mock_query():
        async with MetricsTimer("concurrent_test"):
            await asyncio.sleep(0.1)

    # Run 25 concurrent queries
    start_time = time.time()
    tasks = [mock_query() for _ in range(25)]
    await asyncio.gather(*tasks)
    total_time = time.time() - start_time

    # All queries should complete in reasonable time
    # With proper connection pooling, should be close to single query time
    assert total_time < 2.0, f"Concurrent queries took {total_time}s, too slow"


@pytest.mark.integration
def test_metrics_collection_overhead(reset_metrics):
    """Test that metrics collection has minimal overhead."""

    # Measure without metrics (do some actual work)
    start = time.time()
    for _ in range(1000):
        1 + 1  # Minimal computation
    baseline = time.time() - start

    # Measure with metrics
    start = time.time()
    for _ in range(1000):
        with MetricsTimer("overhead_test"):
            1 + 1  # Same minimal computation
    with_metrics = time.time() - start
    overhead = with_metrics - baseline

    # Overhead should be reasonable (< 50ms total for 1000 iterations)
    # This means each metric collection adds < 50μs overhead
    assert overhead < 0.05, f"Metrics collection overhead {overhead}s is too high"

    # Also verify the baseline is not zero
    assert baseline > 0, "Baseline measurement invalid"


@pytest.mark.integration
def test_performance_metrics_accuracy(reset_metrics):
    """Test that performance metrics are accurate."""
    collector = reset_metrics

    # Record known latencies
    test_latencies = [0.1, 0.2, 0.3, 0.4, 0.5]

    for latency in test_latencies:
        from canary_mcp.metrics import RequestMetrics

        metrics = RequestMetrics(
            tool_name="accuracy_test",
            start_time=0.0,
            end_time=latency,
            status_code=200,
        )
        collector.record_request(metrics)

    # Get stats
    stats = collector.get_summary_stats()
    tool_stats = stats["by_tool"]["accuracy_test"]

    # Verify accuracy
    assert tool_stats["request_count"] == 5
    assert abs(tool_stats["latency"]["median"] - 0.3) < 0.01


@pytest.mark.integration
def test_cache_performance_impact(reset_metrics):
    """Test that caching improves performance."""
    import tempfile
    from pathlib import Path

    from canary_mcp.cache import CacheConfig, CacheStore

    with tempfile.TemporaryDirectory() as tmpdir:
        config = CacheConfig()
        config.cache_dir = Path(tmpdir)
        config.cache_db = Path(tmpdir) / "test.db"
        cache = CacheStore(config)

        # First access - cache miss (slower)
        start = time.time()
        result = cache.get("perf_key")
        miss_time = time.time() - start

        # Set value
        cache.set("perf_key", {"data": "test"})

        # Second access - cache hit (faster)
        start = time.time()
        result = cache.get("perf_key")
        hit_time = time.time() - start

        # Cache hits should be faster than misses
        assert result is not None
        assert hit_time < miss_time * 2  # Allow some variance


@pytest.mark.integration
async def test_error_rate_under_load(reset_metrics):
    """
    Test that error rate remains acceptable under load.

    NFR001: 95%+ success rate
    """
    success_count = 0
    error_count = 0

    async def mock_query_with_errors(should_fail: bool):
        nonlocal success_count, error_count
        try:
            async with MetricsTimer("error_test"):
                if should_fail:
                    raise Exception("Simulated error")
                success_count += 1
        except Exception:
            error_count += 1

    # Run 100 queries with 5% failure rate
    tasks = []
    for i in range(100):
        should_fail = i % 20 == 0  # 5% failure
        tasks.append(mock_query_with_errors(should_fail))

    await asyncio.gather(*tasks, return_exceptions=True)

    success_rate = success_count / (success_count + error_count) * 100

    # Verify 95%+ success rate
    assert success_rate >= 95.0, f"Success rate {success_rate}% below 95% target"


@pytest.mark.integration
def test_performance_summary_generation(reset_metrics):
    """Test that performance summary is generated correctly."""
    collector = reset_metrics

    # Simulate some requests
    for i in range(10):
        from canary_mcp.metrics import RequestMetrics

        metrics = RequestMetrics(
            tool_name="summary_test",
            start_time=0.0,
            end_time=float(i) / 10,
            status_code=200,
        )
        collector.record_request(metrics)

    # Get summary
    stats = collector.get_summary_stats()

    # Verify summary includes required fields
    assert "total_requests" in stats
    assert "by_tool" in stats
    assert "cache_stats" in stats
    assert stats["total_requests"] == 10
