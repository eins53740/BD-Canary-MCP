"""Performance metrics collection and Prometheus export for Canary MCP Server.

Story 2.1: Connection Pooling & Performance Baseline
Collects metrics for request latency, API response times, cache hit/miss rates.
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, DefaultDict


@dataclass
class RequestMetrics:
    """Metrics for a single request."""

    tool_name: str
    start_time: float
    end_time: float
    status_code: int = 200
    error_type: str = ""
    cache_hit: bool = False

    @property
    def duration_seconds(self) -> float:
        """Calculate request duration in seconds."""
        return self.end_time - self.start_time


class MetricsCollector:
    """
    Collects and aggregates performance metrics for MCP server operations.

    Thread-safe metrics collection with support for Prometheus export format.
    Tracks request counts, latencies, and cache statistics per tool.
    """

    def __init__(self) -> None:
        """Initialize metrics collector with empty state."""
        self._lock = Lock()

        # Request counts by tool and status
        self._request_counts: DefaultDict[tuple[str, int], int] = defaultdict(int)

        # Request latencies (stored as histogram buckets)
        self._latency_buckets: DefaultDict[str, list[float]] = defaultdict(list)

        # Cache statistics (for Story 2.2)
        self._cache_hits: DefaultDict[str, int] = defaultdict(int)
        self._cache_misses: DefaultDict[str, int] = defaultdict(int)

        # Connection pool active connections (gauge)
        self._active_connections: int = 0

    def record_request(self, metrics: RequestMetrics) -> None:
        """
        Record a completed request with its metrics.

        Args:
            metrics: RequestMetrics object containing request details
        """
        with self._lock:
            # Increment request count
            key = (metrics.tool_name, metrics.status_code)
            self._request_counts[key] += 1

            # Record latency
            self._latency_buckets[metrics.tool_name].append(metrics.duration_seconds)

            # Record cache statistics
            if metrics.cache_hit:
                self._cache_hits[metrics.tool_name] += 1
            else:
                self._cache_misses[metrics.tool_name] += 1

    def set_active_connections(self, count: int) -> None:
        """
        Update the number of active connections in the pool.

        Args:
            count: Current number of active connections
        """
        with self._lock:
            self._active_connections = count

    def get_summary_stats(self) -> dict[str, Any]:
        """
        Get summary statistics for all recorded metrics.

        Returns:
            dict: Summary statistics including counts, latencies, and cache stats
        """
        with self._lock:
            stats: dict[str, Any] = {
                "total_requests": sum(self._request_counts.values()),
                "by_tool": {},
                "cache_stats": {
                    "total_hits": sum(self._cache_hits.values()),
                    "total_misses": sum(self._cache_misses.values()),
                },
            }

            # Calculate per-tool statistics
            all_tools = set(
                tool for tool, _ in self._request_counts.keys()
            ) | set(self._latency_buckets.keys())

            for tool in all_tools:
                tool_stats: dict[str, Any] = {
                    "request_count": sum(
                        count
                        for (t, _), count in self._request_counts.items()
                        if t == tool
                    ),
                    "cache_hits": self._cache_hits.get(tool, 0),
                    "cache_misses": self._cache_misses.get(tool, 0),
                }

                # Calculate latency percentiles
                latencies = self._latency_buckets.get(tool, [])
                if latencies:
                    sorted_latencies = sorted(latencies)
                    n = len(sorted_latencies)
                    tool_stats["latency"] = {
                        "median": sorted_latencies[n // 2] if n > 0 else 0,
                        "p95": sorted_latencies[int(n * 0.95)] if n > 0 else 0,
                        "p99": sorted_latencies[int(n * 0.99)] if n > 0 else 0,
                        "min": min(sorted_latencies) if sorted_latencies else 0,
                        "max": max(sorted_latencies) if sorted_latencies else 0,
                    }
                else:
                    tool_stats["latency"] = {
                        "median": 0,
                        "p95": 0,
                        "p99": 0,
                        "min": 0,
                        "max": 0,
                    }

                stats["by_tool"][tool] = tool_stats

            stats["active_connections"] = self._active_connections

            return stats

    def export_prometheus(self) -> str:
        """
        Export metrics in Prometheus text exposition format.

        Returns:
            str: Metrics formatted for Prometheus scraping

        Format follows: https://prometheus.io/docs/instrumenting/exposition_formats/
        """
        with self._lock:
            lines: list[str] = []

            # Request count metric
            lines.append("# HELP canary_requests_total Total number of requests by tool")
            lines.append("# TYPE canary_requests_total counter")
            for (tool, status_code), count in self._request_counts.items():
                lines.append(
                    f'canary_requests_total{{tool_name="{tool}",status_code="{status_code}"}} {count}'
                )

            # Request duration histogram
            lines.append(
                "# HELP canary_request_duration_seconds Request duration in seconds"
            )
            lines.append("# TYPE canary_request_duration_seconds histogram")

            for tool, latencies in self._latency_buckets.items():
                if not latencies:
                    continue

                sorted_latencies = sorted(latencies)
                n = len(sorted_latencies)

                # Histogram buckets (0.1s, 0.5s, 1s, 2.5s, 5s, 10s, +Inf)
                buckets = [0.1, 0.5, 1.0, 2.5, 5.0, 10.0, float("inf")]
                cumulative = 0

                for bucket in buckets:
                    count = sum(1 for lat in latencies if lat <= bucket)
                    cumulative += count
                    bucket_str = "+Inf" if bucket == float("inf") else str(bucket)
                    lines.append(
                        f'canary_request_duration_seconds_bucket{{tool_name="{tool}",le="{bucket_str}"}} {cumulative}'
                    )

                # Summary statistics
                total = sum(latencies)
                lines.append(
                    f'canary_request_duration_seconds_sum{{tool_name="{tool}"}} {total:.6f}'
                )
                lines.append(
                    f'canary_request_duration_seconds_count{{tool_name="{tool}"}} {n}'
                )

            # Cache hit/miss metrics
            lines.append("# HELP canary_cache_hits_total Total number of cache hits")
            lines.append("# TYPE canary_cache_hits_total counter")
            for tool, hits in self._cache_hits.items():
                lines.append(f'canary_cache_hits_total{{tool_name="{tool}"}} {hits}')

            lines.append("# HELP canary_cache_misses_total Total number of cache misses")
            lines.append("# TYPE canary_cache_misses_total counter")
            for tool, misses in self._cache_misses.items():
                lines.append(f'canary_cache_misses_total{{tool_name="{tool}"}} {misses}')

            # Active connections gauge
            lines.append(
                "# HELP canary_pool_connections_active Number of active connections in pool"
            )
            lines.append("# TYPE canary_pool_connections_active gauge")
            lines.append(f"canary_pool_connections_active {self._active_connections}")

            return "\n".join(lines) + "\n"

    def reset(self) -> None:
        """Reset all metrics (useful for testing)."""
        with self._lock:
            self._request_counts.clear()
            self._latency_buckets.clear()
            self._cache_hits.clear()
            self._cache_misses.clear()
            self._active_connections = 0


# Global metrics collector instance
_metrics_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """
    Get the global metrics collector instance.

    Returns:
        MetricsCollector: The global metrics collector
    """
    return _metrics_collector


class MetricsTimer:
    """
    Context manager for timing requests and recording metrics.

    Usage:
        async with MetricsTimer("search_tags"):
            result = await perform_search()
    """

    def __init__(self, tool_name: str) -> None:
        """
        Initialize metrics timer for a specific tool.

        Args:
            tool_name: Name of the MCP tool being measured
        """
        self.tool_name = tool_name
        self.start_time = 0.0
        self.status_code = 200
        self.error_type = ""
        self.cache_hit = False

    def __enter__(self) -> "MetricsTimer":
        """Start timing."""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore
        """Stop timing and record metrics."""
        end_time = time.time()

        # Determine status code from exception
        if exc_type is not None:
            self.status_code = 500
            self.error_type = exc_type.__name__

        metrics = RequestMetrics(
            tool_name=self.tool_name,
            start_time=self.start_time,
            end_time=end_time,
            status_code=self.status_code,
            error_type=self.error_type,
            cache_hit=self.cache_hit,
        )

        get_metrics_collector().record_request(metrics)

    async def __aenter__(self) -> "MetricsTimer":
        """Async context manager entry."""
        return self.__enter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore
        """Async context manager exit."""
        self.__exit__(exc_type, exc_val, exc_tb)
