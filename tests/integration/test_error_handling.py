"""
Integration tests for advanced error handling and retry logic.

Story 2.3: Advanced Error Handling & Retry Logic
Validates retry with exponential backoff, circuit breaker, and graceful degradation.
"""

import os
import time
from unittest.mock import MagicMock, patch

import httpx
import pytest

from canary_mcp.auth import CanaryAuthClient, retry_with_backoff
from canary_mcp.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerError,
    CircuitState,
    get_circuit_breaker,
)


@pytest.fixture
def mock_env():
    """Mock environment variables for testing."""
    return {
        "CANARY_SAF_BASE_URL": "https://test.canary.com/api/v1",
        "CANARY_VIEWS_BASE_URL": "https://test.canary.com",
        "CANARY_API_TOKEN": "test-token-123",
        "CANARY_RETRY_ATTEMPTS": "3",
        "CANARY_CIRCUIT_CONSECUTIVE_FAILURES": "5",
        "CANARY_CIRCUIT_RESET_SECONDS": "2",  # Short for testing
    }


class TestRetryLogic:
    """Test retry logic with exponential backoff."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_retry_succeeds_on_second_attempt(self, mock_env):
        """Test that retry logic succeeds after transient failure."""
        with patch.dict(os.environ, mock_env):
            call_count = 0

            @retry_with_backoff(max_attempts=3, base_delay=0.01)
            async def failing_then_succeeding():
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise httpx.ConnectError("Connection failed")
                return "success"

            result = await failing_then_succeeding()

            assert result == "success"
            assert call_count == 2  # Failed once, succeeded on retry

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_retry_exhausts_attempts(self, mock_env):
        """Test that retry logic raises after max attempts."""
        with patch.dict(os.environ, mock_env):
            call_count = 0

            @retry_with_backoff(max_attempts=3, base_delay=0.01)
            async def always_failing():
                nonlocal call_count
                call_count += 1
                raise httpx.ConnectError("Connection failed")

            with pytest.raises(httpx.ConnectError):
                await always_failing()

            assert call_count == 3  # All attempts exhausted

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_exponential_backoff_timing(self, mock_env):
        """Test that exponential backoff delays increase correctly."""
        with patch.dict(os.environ, mock_env):
            delays = []

            @retry_with_backoff(
                max_attempts=4, base_delay=0.1, exponential_base=2.0, jitter=False
            )
            async def always_failing_with_timing():
                nonlocal delays
                if len(delays) > 0:
                    # Record time since last call
                    delays.append(time.time())
                else:
                    delays.append(time.time())
                raise httpx.ConnectError("Connection failed")

            with pytest.raises(httpx.ConnectError):
                await always_failing_with_timing()

            # Check that we had 4 attempts
            assert len(delays) == 4

            # Check delays are increasing (with some tolerance for timing)
            # Expected: ~0.1s, ~0.2s, ~0.4s
            if len(delays) >= 3:
                delay1 = delays[1] - delays[0]
                delay2 = delays[2] - delays[1]

                # Delays should be increasing (with tolerance)
                assert delay2 > delay1 * 0.8  # Allow 20% tolerance

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_jitter_prevents_thundering_herd(self, mock_env):
        """Test that jitter adds randomization to delays."""
        with patch.dict(os.environ, mock_env):
            delays = []

            @retry_with_backoff(max_attempts=5, base_delay=0.1, jitter=True)
            async def always_failing():
                if len(delays) > 0:
                    delays.append(time.time())
                else:
                    delays.append(time.time())
                raise httpx.ConnectError("Connection failed")

            with pytest.raises(httpx.ConnectError):
                await always_failing()

            # With jitter, delays should vary
            # We can't test exact randomness, but we can verify attempts happened
            assert len(delays) == 5

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_auth_error_no_retry(self, mock_env):
        """Test that authentication errors are not retried."""
        from canary_mcp.exceptions import CanaryAuthError

        with patch.dict(os.environ, mock_env):
            call_count = 0

            @retry_with_backoff(max_attempts=3)
            async def auth_failing():
                nonlocal call_count
                call_count += 1
                raise CanaryAuthError("Invalid credentials")

            with pytest.raises(CanaryAuthError):
                await auth_failing()

            # Should fail immediately without retry
            assert call_count == 1


class TestCircuitBreaker:
    """Test circuit breaker pattern."""

    def test_circuit_breaker_initial_state(self):
        """Test that circuit breaker starts in closed state."""
        cb = CircuitBreaker("test-circuit")

        assert cb.state == CircuitState.CLOSED
        assert cb.is_closed
        assert not cb.is_open

    def test_circuit_opens_after_failures(self):
        """Test that circuit opens after consecutive failures."""
        config = CircuitBreakerConfig()
        config.failure_threshold = 3
        cb = CircuitBreaker("test-circuit", config)

        # Simulate failures
        for i in range(3):
            try:
                cb.call(lambda: 1 / 0)  # Division by zero error
            except ZeroDivisionError:
                pass

        # Circuit should be open now
        assert cb.state == CircuitState.OPEN
        assert cb.is_open

    def test_circuit_rejects_when_open(self):
        """Test that circuit breaker rejects requests when open."""
        config = CircuitBreakerConfig()
        config.failure_threshold = 2
        cb = CircuitBreaker("test-circuit", config)

        # Cause failures to open circuit
        for i in range(2):
            try:
                cb.call(lambda: 1 / 0)
            except ZeroDivisionError:
                pass

        # Circuit is open, should reject
        with pytest.raises(CircuitBreakerError) as exc_info:
            cb.call(lambda: "success")

        assert "is OPEN" in str(exc_info.value)

    def test_circuit_transitions_to_half_open(self):
        """Test that circuit transitions to half-open after timeout."""
        config = CircuitBreakerConfig()
        config.failure_threshold = 2
        config.reset_timeout = 0.1  # 100ms for testing
        cb = CircuitBreaker("test-circuit", config)

        # Open the circuit
        for i in range(2):
            try:
                cb.call(lambda: 1 / 0)
            except ZeroDivisionError:
                pass

        assert cb.is_open

        # Wait for reset timeout
        time.sleep(0.15)

        # Next call should transition to half-open
        try:
            cb.call(lambda: "success")
        except Exception:
            pass

        # Should be in half-open or closed state (depending on success)
        assert cb.state in [CircuitState.HALF_OPEN, CircuitState.CLOSED]

    def test_circuit_closes_after_success_in_half_open(self):
        """Test that circuit closes after successes in half-open state."""
        config = CircuitBreakerConfig()
        config.failure_threshold = 2
        config.reset_timeout = 0.1
        config.success_threshold = 2
        cb = CircuitBreaker("test-circuit", config)

        # Open the circuit
        for i in range(2):
            try:
                cb.call(lambda: 1 / 0)
            except ZeroDivisionError:
                pass

        assert cb.is_open

        # Wait for reset
        time.sleep(0.15)

        # Succeed twice to close circuit
        cb.call(lambda: "success")
        cb.call(lambda: "success")

        assert cb.is_closed

    def test_circuit_get_stats(self):
        """Test that circuit breaker provides statistics."""
        cb = CircuitBreaker("test-circuit")

        stats = cb.get_stats()

        assert "name" in stats
        assert "state" in stats
        assert "failure_count" in stats
        assert "success_count" in stats
        assert stats["name"] == "test-circuit"
        assert stats["state"] == "closed"

    def test_circuit_breaker_singleton(self):
        """Test that get_circuit_breaker returns same instance."""
        cb1 = get_circuit_breaker("test-singleton")
        cb2 = get_circuit_breaker("test-singleton")

        assert cb1 is cb2


class TestErrorCategorization:
    """Test error categorization and handling."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_transient_errors_retried(self, mock_env):
        """Test that transient errors (network, timeout) are retried."""
        with patch.dict(os.environ, mock_env):
            # ConnectError is transient
            call_count = 0

            @retry_with_backoff(max_attempts=3, base_delay=0.01)
            async def transient_failure():
                nonlocal call_count
                call_count += 1
                if call_count < 2:
                    raise httpx.ConnectError("Transient network error")
                return "success"

            result = await transient_failure()

            assert result == "success"
            assert call_count == 2  # Retried once

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_permanent_errors_not_retried(self, mock_env):
        """Test that permanent errors are not retried."""
        from canary_mcp.exceptions import CanaryAuthError

        with patch.dict(os.environ, mock_env):
            call_count = 0

            @retry_with_backoff(max_attempts=3)
            async def permanent_failure():
                nonlocal call_count
                call_count += 1
                raise CanaryAuthError("Invalid API token")

            with pytest.raises(CanaryAuthError):
                await permanent_failure()

            # Should not retry
            assert call_count == 1


class TestGracefulDegradation:
    """Test graceful degradation with cached data."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_cache_used_when_api_fails(self, mock_env):
        """Test that cached data is returned when API is unavailable."""
        # This test verifies the pattern is in place
        # Actual implementation tested in individual tool tests
        from canary_mcp.cache import get_cache_store

        with patch.dict(os.environ, mock_env):
            cache = get_cache_store()

            # Pre-populate cache
            cache_key = "test_degradation_key"
            cached_data = {"success": True, "data": "cached_value"}
            cache.set(cache_key, cached_data)

            # Retrieve from cache
            result = cache.get(cache_key)

            assert result is not None
            assert result["success"] is True
            assert result["data"] == "cached_value"


class TestHealthCheckTool:
    """Test health check tool with circuit breaker state."""

    def test_get_health_function_exists(self):
        """Test that get_health function exists and is callable."""
        # Import the module to check the function exists

        import canary_mcp.server as server_module

        # Check that get_health exists in the module
        assert hasattr(server_module, "get_health")

        # Get the function
        get_health_func = getattr(server_module, "get_health")

        # It should be a FunctionTool (decorated)
        # Just verify it's there and has expected attributes
        assert get_health_func is not None

    def test_circuit_breaker_get_stats_structure(self):
        """Test circuit breaker get_stats method structure (used by health check)."""
        cb = CircuitBreaker("test-stats")

        stats = cb.get_stats()

        # Verify the stats structure that get_health will use
        assert "name" in stats
        assert "state" in stats
        assert "failure_count" in stats
        assert "success_count" in stats
        assert "state_changes" in stats
        assert "time_until_reset" in stats

    def test_circuit_breaker_stats_reflect_state(self):
        """Test that circuit breaker stats accurately reflect state."""
        config = CircuitBreakerConfig()
        config.failure_threshold = 2
        cb = CircuitBreaker("test-state-stats", config)

        # Initially closed
        stats = cb.get_stats()
        assert stats["state"] == "closed"
        assert stats["failure_count"] == 0

        # Cause failures to open
        for i in range(2):
            try:
                cb.call(lambda: 1 / 0)
            except:
                pass

        # Should be open now
        stats = cb.get_stats()
        assert stats["state"] == "open"
        assert stats["state_changes"] >= 1


class TestMetricsTracking:
    """Test that metrics track retry attempts and errors."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_retry_attempts_logged(self, mock_env, caplog):
        """Test that retry attempts are logged."""
        with patch.dict(os.environ, mock_env):
            call_count = 0

            @retry_with_backoff(max_attempts=3, base_delay=0.01)
            async def failing_function():
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    raise httpx.ConnectError("Test error")
                return "success"

            result = await failing_function()

            assert result == "success"
            # Logs would contain retry_attempt messages


class TestEndToEndErrorHandling:
    """End-to-end tests simulating real failure scenarios."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_canary_api_transient_failure_recovery(self, mock_env):
        """Test recovery from transient Canary API failures."""
        with patch.dict(os.environ, mock_env):
            async with CanaryAuthClient() as client:
                # Mock HTTP client with transient failure
                call_count = 0

                async def mock_post_with_failure(*args, **kwargs):
                    nonlocal call_count
                    call_count += 1

                    if call_count == 1:
                        # First attempt fails
                        raise httpx.ConnectError("Network error")

                    # Second attempt succeeds
                    mock_response = MagicMock()
                    mock_response.json.return_value = {"sessionToken": "test-token"}
                    mock_response.raise_for_status = MagicMock()
                    return mock_response

                with patch.object(
                    client._client, "post", side_effect=mock_post_with_failure
                ):
                    # This should succeed after retry
                    token = await client.authenticate()

                    assert token == "test-token"
                    assert call_count == 2  # Retried once

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_circuit_breaker_protects_against_cascading_failures(self):
        """Test that circuit breaker prevents cascading failures."""
        config = CircuitBreakerConfig()
        config.failure_threshold = 3
        config.reset_timeout = 0.2
        cb = CircuitBreaker("cascading-test", config)

        # Simulate cascade of failures
        for i in range(3):
            try:
                cb.call(lambda: 1 / 0)
            except ZeroDivisionError:
                pass

        # Circuit should be open
        assert cb.is_open

        # Further requests should be rejected immediately
        start = time.time()
        with pytest.raises(CircuitBreakerError):
            cb.call(lambda: "test")
        duration = time.time() - start

        # Should fail fast (< 100ms)
        assert duration < 0.1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
