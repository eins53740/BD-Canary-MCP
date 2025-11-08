"""
Circuit breaker pattern implementation for Canary MCP Server.

Story 2.3: Advanced Error Handling & Retry Logic
Protects against cascading failures by temporarily stopping requests to failing services.
"""

import os
import time
from dataclasses import dataclass
from enum import Enum
from threading import Lock
from typing import Optional

from canary_mcp.logging_setup import get_logger

log = get_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""

    def __init__(self):
        """Initialize circuit breaker configuration from environment."""
        # Failure threshold
        self.failure_threshold = int(
            os.getenv("CANARY_CIRCUIT_CONSECUTIVE_FAILURES", "5")
        )

        # Cooldown period before attempting recovery (seconds)
        self.reset_timeout = int(os.getenv("CANARY_CIRCUIT_RESET_SECONDS", "60"))

        # Success threshold in half-open state before closing
        self.success_threshold = 2


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""

    pass


class CircuitBreaker:
    """
    Circuit breaker to prevent cascading failures.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, reject requests immediately
    - HALF_OPEN: Testing if service recovered, limited requests allowed

    Transitions:
    - CLOSED -> OPEN: After failure_threshold consecutive failures
    - OPEN -> HALF_OPEN: After reset_timeout seconds
    - HALF_OPEN -> CLOSED: After success_threshold consecutive successes
    - HALF_OPEN -> OPEN: On any failure
    """

    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        """
        Initialize circuit breaker.

        Args:
            name: Name of the circuit (for logging/identification)
            config: Circuit breaker configuration
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._lock = Lock()

        # State tracking
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._state_change_count = 0

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        with self._lock:
            return self._state

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (rejecting requests)."""
        return self.state == CircuitState.OPEN

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self.state == CircuitState.CLOSED

    def call(self, func, *args, **kwargs):
        """
        Execute function through circuit breaker.

        Args:
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            Result of function call

        Raises:
            CircuitBreakerError: If circuit is open
        """
        # Check if we should allow the request
        with self._lock:
            if self._state == CircuitState.OPEN:
                # Check if enough time has passed to try recovery
                if self._should_attempt_reset():
                    self._transition_to_half_open()
                else:
                    raise CircuitBreakerError(
                        f"Circuit breaker '{self.name}' is OPEN. "
                        f"Service unavailable, will retry in "
                        f"{self._time_until_reset():.0f}s"
                    )

        # Attempt the call
        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result

        except Exception:
            self._record_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self._last_failure_time is None:
            return True

        elapsed = time.time() - self._last_failure_time
        return elapsed >= self.config.reset_timeout

    def _time_until_reset(self) -> float:
        """Calculate time remaining until reset attempt."""
        if self._last_failure_time is None:
            return 0

        elapsed = time.time() - self._last_failure_time
        remaining = self.config.reset_timeout - elapsed
        return max(0, remaining)

    def _record_success(self) -> None:
        """Record successful call."""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1

                if self._success_count >= self.config.success_threshold:
                    self._transition_to_closed()
            elif self._state == CircuitState.CLOSED:
                # Reset failure count on success
                self._failure_count = 0

    def _record_failure(self) -> None:
        """Record failed call."""
        with self._lock:
            self._last_failure_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                # Any failure in half-open immediately opens circuit
                self._transition_to_open()
            elif self._state == CircuitState.CLOSED:
                self._failure_count += 1

                if self._failure_count >= self.config.failure_threshold:
                    self._transition_to_open()

    def _transition_to_open(self) -> None:
        """Transition to OPEN state."""
        old_state = self._state
        self._state = CircuitState.OPEN
        self._failure_count = 0
        self._success_count = 0
        self._state_change_count += 1

        log.warning(
            "circuit_breaker_opened",
            circuit=self.name,
            old_state=old_state.value,
            new_state=CircuitState.OPEN.value,
            reset_timeout=self.config.reset_timeout,
        )

    def _transition_to_half_open(self) -> None:
        """Transition to HALF_OPEN state."""
        old_state = self._state
        self._state = CircuitState.HALF_OPEN
        self._success_count = 0
        self._state_change_count += 1

        log.info(
            "circuit_breaker_half_open",
            circuit=self.name,
            old_state=old_state.value,
            new_state=CircuitState.HALF_OPEN.value,
        )

    def _transition_to_closed(self) -> None:
        """Transition to CLOSED state."""
        old_state = self._state
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._state_change_count += 1

        log.info(
            "circuit_breaker_closed",
            circuit=self.name,
            old_state=old_state.value,
            new_state=CircuitState.CLOSED.value,
        )

    def get_stats(self) -> dict:
        """
        Get circuit breaker statistics.

        Returns:
            dict: Statistics including state, counts, timing
        """
        with self._lock:
            return {
                "name": self.name,
                "state": self._state.value,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                "state_changes": self._state_change_count,
                "time_until_reset": (
                    self._time_until_reset() if self._state == CircuitState.OPEN else 0
                ),
                "failure_threshold": self.config.failure_threshold,
                "reset_timeout": self.config.reset_timeout,
            }

    def reset(self) -> None:
        """Manually reset circuit breaker to CLOSED state."""
        with self._lock:
            old_state = self._state
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._last_failure_time = None

            log.info(
                "circuit_breaker_manual_reset",
                circuit=self.name,
                old_state=old_state.value,
            )


# Global circuit breaker instances
_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(name: str) -> CircuitBreaker:
    """
    Get or create a circuit breaker instance.

    Args:
        name: Circuit breaker name

    Returns:
        CircuitBreaker: The circuit breaker instance
    """
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(name)
    return _circuit_breakers[name]


def get_all_circuit_breakers() -> dict[str, CircuitBreaker]:
    """
    Get all circuit breaker instances.

    Returns:
        dict: Mapping of circuit names to CircuitBreaker instances
    """
    return _circuit_breakers.copy()
