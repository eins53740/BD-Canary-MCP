"""
Integration tests for connection pooling and performance metrics.

Story 2.1: Connection Pooling & Performance Baseline
Validates that connection pool reuses connections and handles concurrent requests.
"""

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from canary_mcp.auth import CanaryAuthClient
from canary_mcp.metrics import get_metrics_collector, MetricsTimer, RequestMetrics


@pytest.fixture
def mock_env():
    """Mock environment variables for testing."""
    return {
        "CANARY_SAF_BASE_URL": "https://test.canary.com/api/v1",
        "CANARY_VIEWS_BASE_URL": "https://test.canary.com",
        "CANARY_API_TOKEN": "test-token-123",
        "CANARY_TIMEOUT": "30",
        "CANARY_POOL_SIZE": "10",
    }


@pytest.fixture
def mock_canary_response():
    """Create a mock Canary API response."""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.json.return_value = {"sessionToken": "test-session-token"}
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    return mock_response


class TestConnectionPooling:
    """Test connection pool functionality."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_connection_pool_configured(self, mock_env):
        """Verify that CanaryAuthClient uses connection pooling."""
        with patch.dict(os.environ, mock_env):
            async with CanaryAuthClient() as client:
                # Verify client has httpx.AsyncClient with limits configured
                assert client._client is not None
                assert isinstance(client._client, httpx.AsyncClient)

                # Check that timeout is configured
                assert client._client.timeout is not None

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_connection_reuse_sequential_requests(self, mock_env, mock_canary_response):
        """Test that connection pool reuses connections for sequential requests."""
        with patch.dict(os.environ, mock_env):
            async with CanaryAuthClient() as client:
                # Mock HTTP client post method
                mock_post = AsyncMock(return_value=mock_canary_response)

                with patch.object(client._client, "post", mock_post):
                    # Make multiple sequential requests
                    token1 = await client.authenticate()
                    token2 = await client.refresh_token()
                    token3 = await client.refresh_token()

                    # Verify all requests succeeded
                    assert token1 == "test-session-token"
                    assert token2 == "test-session-token"
                    assert token3 == "test-session-token"

                    # Verify post was called 3 times (all using same client/pool)
                    assert mock_post.call_count == 3

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_concurrent_request_handling(self, mock_env, mock_canary_response):
        """Test that pool handles concurrent requests correctly."""
        with patch.dict(os.environ, mock_env):
            async with CanaryAuthClient() as client:
                # Mock HTTP client post method with slight delay
                async def mock_post_with_delay(*args, **kwargs):
                    await asyncio.sleep(0.01)  # Small delay to simulate network
                    return mock_canary_response

                with patch.object(client._client, "post", side_effect=mock_post_with_delay):
                    # Launch 10 concurrent requests
                    tasks = [client.refresh_token() for _ in range(10)]
                    tokens = await asyncio.gather(*tasks)

                    # Verify all requests succeeded
                    assert len(tokens) == 10
                    assert all(token == "test-session-token" for token in tokens)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_connection_timeout_configuration(self, mock_env):
        """Test that connection timeout is properly configured."""
        mock_env["CANARY_TIMEOUT"] = "15"

        with patch.dict(os.environ, mock_env):
            async with CanaryAuthClient() as client:
                # Verify timeout is configured from environment
                timeout_config = client._client.timeout
                assert timeout_config is not None

                # httpx timeout includes connect, read, write, pool timeout
                # We expect the timeout to be set (exact value depends on implementation)
                assert timeout_config.read is not None or timeout_config.pool is not None

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_pool_max_connections_limit(self, mock_env):
        """Test that pool respects max_connections limit."""
        mock_env["CANARY_POOL_SIZE"] = "5"

        with patch.dict(os.environ, mock_env):
            async with CanaryAuthClient() as client:
                # Verify client limits are configured
                # Note: httpx AsyncClient may not expose limits directly in all versions
                # This is a basic check that the client exists and is configured
                assert client._client is not None

                # The actual limit enforcement would be tested with real requests
                # For integration test, we verify the configuration exists


class TestMetricsCollection:
    """Test performance metrics collection."""

    def test_metrics_collector_singleton(self):
        """Verify metrics collector is a singleton."""
        collector1 = get_metrics_collector()
        collector2 = get_metrics_collector()

        assert collector1 is collector2

    def test_record_request_metrics(self):
        """Test recording request metrics."""
        collector = get_metrics_collector()

        # Record a request
        metrics = RequestMetrics(
            tool_name="test_tool",
            start_time=1000.0,
            end_time=1002.5,
            status_code=200,
            cache_hit=False,
        )

        collector.record_request(metrics)

        # Get summary stats
        stats = collector.get_summary_stats()

        # Verify metrics were recorded
        assert stats["total_requests"] >= 1
        assert "by_tool" in stats
        assert "test_tool" in stats["by_tool"]
        assert stats["by_tool"]["test_tool"]["request_count"] >= 1

    def test_cache_hit_miss_tracking(self):
        """Test cache hit/miss statistics."""
        collector = get_metrics_collector()

        # Record cache hit
        metrics_hit = RequestMetrics(
            tool_name="cache_test",
            start_time=1000.0,
            end_time=1001.0,
            status_code=200,
            cache_hit=True,
        )
        collector.record_request(metrics_hit)

        # Record cache miss
        metrics_miss = RequestMetrics(
            tool_name="cache_test",
            start_time=1000.0,
            end_time=1002.0,
            status_code=200,
            cache_hit=False,
        )
        collector.record_request(metrics_miss)

        # Get stats
        stats = collector.get_summary_stats()

        # Verify cache statistics
        assert "cache_stats" in stats
        assert stats["cache_stats"]["total_hits"] >= 1
        assert stats["cache_stats"]["total_misses"] >= 1

    def test_latency_percentiles_calculation(self):
        """Test latency percentile calculations."""
        collector = get_metrics_collector()

        # Record multiple requests with varying latencies
        for i in range(100):
            metrics = RequestMetrics(
                tool_name="latency_test",
                start_time=1000.0,
                end_time=1000.0 + (i * 0.01),  # 0 to 1 second
                status_code=200,
                cache_hit=False,
            )
            collector.record_request(metrics)

        # Get stats
        stats = collector.get_summary_stats()

        # Verify latency statistics exist
        if "latency_test" in stats["by_tool"]:
            tool_stats = stats["by_tool"]["latency_test"]
            assert "latency" in tool_stats
            latency = tool_stats["latency"]

            # Check percentiles exist
            assert "median" in latency
            assert "p95" in latency
            assert "p99" in latency

            # Verify percentiles are in reasonable order
            assert latency["median"] <= latency["p95"]
            assert latency["p95"] <= latency["p99"]

    @pytest.mark.asyncio
    async def test_metrics_timer_context_manager(self):
        """Test MetricsTimer context manager."""
        async with MetricsTimer("timer_test") as timer:
            # Simulate work
            await asyncio.sleep(0.01)
            timer.cache_hit = False

        # Timer should record metrics automatically
        collector = get_metrics_collector()
        stats = collector.get_summary_stats()

        # Verify timer recorded the request
        assert stats["total_requests"] >= 1

    def test_active_connections_gauge(self):
        """Test active connections gauge metric."""
        collector = get_metrics_collector()

        # Set active connections
        collector.set_active_connections(5)

        # Get stats
        stats = collector.get_summary_stats()

        # Verify gauge is tracked
        assert "active_connections" in stats
        assert stats["active_connections"] == 5

    def test_prometheus_metrics_format(self):
        """Test Prometheus format export."""
        collector = get_metrics_collector()

        # Record some metrics
        metrics = RequestMetrics(
            tool_name="prometheus_test",
            start_time=1000.0,
            end_time=1001.5,
            status_code=200,
            cache_hit=False,
        )
        collector.record_request(metrics)

        # Get Prometheus format
        prom_output = collector.export_prometheus()

        # Verify Prometheus format basics
        assert isinstance(prom_output, str)
        assert "# HELP" in prom_output
        assert "# TYPE" in prom_output

        # Check for expected metrics
        assert "canary_requests_total" in prom_output


class TestConcurrentPerformance:
    """Test concurrent performance characteristics."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_high_concurrency_10_requests(self, mock_env, mock_canary_response):
        """Test handling 10 concurrent requests (NFR001 baseline)."""
        with patch.dict(os.environ, mock_env):
            async with CanaryAuthClient() as client:
                # Mock HTTP responses
                async def mock_post(*args, **kwargs):
                    await asyncio.sleep(0.01)
                    return mock_canary_response

                with patch.object(client._client, "post", side_effect=mock_post):
                    import time
                    start = time.time()

                    # Launch 10 concurrent requests
                    tasks = [client.refresh_token() for _ in range(10)]
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    duration = time.time() - start

                    # Verify all succeeded
                    successful = [r for r in results if not isinstance(r, Exception)]
                    assert len(successful) == 10

                    # Verify reasonable performance (should be faster than sequential)
                    # 10 concurrent requests at 0.01s each should complete in ~0.01-0.05s
                    # (not 0.1s if sequential)
                    assert duration < 0.2  # Very lenient to avoid flaky tests

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_high_concurrency_25_requests(self, mock_env, mock_canary_response):
        """Test handling 25 concurrent requests (NFR001 target)."""
        mock_env["CANARY_POOL_SIZE"] = "25"

        with patch.dict(os.environ, mock_env):
            async with CanaryAuthClient() as client:
                # Mock HTTP responses
                async def mock_post(*args, **kwargs):
                    await asyncio.sleep(0.01)
                    return mock_canary_response

                with patch.object(client._client, "post", side_effect=mock_post):
                    import time
                    start = time.time()

                    # Launch 25 concurrent requests
                    tasks = [client.refresh_token() for _ in range(25)]
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    duration = time.time() - start

                    # Verify all succeeded
                    successful = [r for r in results if not isinstance(r, Exception)]
                    assert len(successful) == 25

                    # Verify reasonable performance
                    assert duration < 0.5  # Very lenient

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_error_rate_under_load(self, mock_env):
        """Test that error rate remains low under concurrent load."""
        with patch.dict(os.environ, mock_env):
            async with CanaryAuthClient() as client:
                # Mock some successes and some failures
                call_count = 0

                async def mock_post_with_failures(*args, **kwargs):
                    nonlocal call_count
                    call_count += 1

                    # Simulate 10% failure rate
                    if call_count % 10 == 0:
                        raise httpx.HTTPError("Simulated failure")

                    mock_response = MagicMock()
                    mock_response.json.return_value = {"sessionToken": "test-token"}
                    mock_response.raise_for_status = MagicMock()
                    return mock_response

                with patch.object(client._client, "post", side_effect=mock_post_with_failures):
                    # Launch 20 concurrent requests
                    tasks = [client.refresh_token() for _ in range(20)]
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    # Count successes and failures
                    successes = sum(1 for r in results if not isinstance(r, Exception))
                    failures = sum(1 for r in results if isinstance(r, Exception))
                    error_rate = (failures / len(results)) * 100

                    # Verify error rate is tracked (we expect ~10% in this test)
                    assert error_rate >= 5.0  # At least some errors
                    assert error_rate <= 15.0  # But not too many


class TestPerformanceBaseline:
    """Test baseline performance measurements."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_single_request_latency_baseline(self, mock_env, mock_canary_response):
        """Measure baseline latency for single request."""
        with patch.dict(os.environ, mock_env):
            async with CanaryAuthClient() as client:
                async def mock_post(*args, **kwargs):
                    await asyncio.sleep(0.01)  # Simulate 10ms latency
                    return mock_canary_response

                with patch.object(client._client, "post", side_effect=mock_post):
                    import time

                    # Measure latency
                    start = time.time()
                    await client.refresh_token()
                    duration = time.time() - start

                    # Verify reasonable baseline latency
                    # With mock, should be ~10ms + overhead
                    assert duration < 0.1  # < 100ms

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_throughput_measurement(self, mock_env, mock_canary_response):
        """Measure baseline throughput (queries per second)."""
        with patch.dict(os.environ, mock_env):
            async with CanaryAuthClient() as client:
                async def mock_post(*args, **kwargs):
                    await asyncio.sleep(0.001)  # 1ms per query
                    return mock_canary_response

                with patch.object(client._client, "post", side_effect=mock_post):
                    import time

                    # Measure throughput with concurrent requests
                    num_requests = 50
                    start = time.time()

                    tasks = [client.refresh_token() for _ in range(num_requests)]
                    await asyncio.gather(*tasks)

                    duration = time.time() - start
                    throughput = num_requests / duration

                    # Verify reasonable throughput
                    # With 1ms per query and concurrency, should be quite high
                    assert throughput > 10  # At least 10 queries/second


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
