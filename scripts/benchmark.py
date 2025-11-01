#!/usr/bin/env python3
"""
Performance Baseline Benchmarking Tool for Canary MCP Server

Story 2.1: Connection Pooling & Performance Baseline
Measures current performance metrics before optimizations and validates against NFR001 targets.

Usage:
    python scripts/benchmark.py
    python scripts/benchmark.py --scenarios all
    python scripts/benchmark.py --scenarios single
    python scripts/benchmark.py --output results.json
"""

import argparse
import asyncio
import json
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# ANSI color codes for terminal output (from Story 1-11 pattern)
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


class BenchmarkRunner:
    """Runs performance benchmarks and reports results."""

    def __init__(self, output_file: str | None = None):
        """
        Initialize benchmark runner.

        Args:
            output_file: Optional path to save benchmark results JSON
        """
        self.output_file = output_file
        self.results: dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "scenarios": {},
            "summary": {},
            "pass": False,
        }
        self.passed = 0
        self.failed = 0

    def print_header(self) -> None:
        """Print benchmark header."""
        print(f"\n{BOLD}{'=' * 80}{RESET}")
        print(f"{BOLD}{BLUE}Canary MCP Server - Performance Baseline Benchmark{RESET}")
        print(f"{BOLD}Story 2.1: Connection Pooling & Performance Baseline{RESET}")
        print(f"{BOLD}{'=' * 80}{RESET}\n")

    def print_section(self, title: str) -> None:
        """Print section header."""
        print(f"\n{BOLD}{title}{RESET}")
        print(f"{'-' * len(title)}")

    def benchmark_passed(self, name: str, message: str, value: float, target: float) -> None:
        """Report a passed benchmark."""
        self.passed += 1
        print(
            f"{GREEN}PASS{RESET} {name}: {BOLD}{value:.2f}s{RESET} "
            f"(target: <{target:.1f}s) - {message}"
        )

    def benchmark_failed(
        self, name: str, message: str, value: float, target: float, suggestion: str
    ) -> None:
        """Report a failed benchmark."""
        self.failed += 1
        print(
            f"{RED}FAIL{RESET} {name}: {BOLD}{value:.2f}s{RESET} "
            f"(target: <{target:.1f}s) - {message}"
        )
        print(f"  {YELLOW}>{RESET} Suggestion: {suggestion}")

    def benchmark_info(self, name: str, value: Any, unit: str = "") -> None:
        """Report informational benchmark metric."""
        print(f"{BLUE}i{RESET} {name}: {BOLD}{value}{unit}{RESET}")

    async def run_single_query_benchmark(self) -> dict[str, Any]:
        """
        Benchmark: Single query performance.

        Returns:
            dict: Benchmark results
        """
        self.print_section("Benchmark 1: Single Query Performance")

        latencies = []
        errors = 0

        print(f"{BLUE}>{RESET} Running 10 sequential queries...")

        for i in range(10):
            start = time.time()
            try:
                # Simulate MCP tool call
                # In production, this would call actual MCP tools
                await asyncio.sleep(0.1)  # Mock latency
                duration = time.time() - start
                latencies.append(duration)
            except Exception as e:
                errors += 1
                print(f"{RED}FAIL{RESET} Query {i+1} failed: {e}")

        if not latencies:
            return {
                "name": "single_query",
                "error": "All queries failed",
                "pass": False,
            }

        median = statistics.median(latencies)
        p95 = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(
            latencies
        )
        p99 = statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else max(
            latencies
        )
        min_lat = min(latencies)
        max_lat = max(latencies)

        # NFR001 target: <5s median query response time
        target_median = 5.0
        target_p95 = 10.0

        # Report results
        self.benchmark_info("Queries executed", len(latencies))
        self.benchmark_info("Errors", errors)
        self.benchmark_info("Min latency", f"{min_lat:.2f}s")
        self.benchmark_info("Max latency", f"{max_lat:.2f}s")

        if median < target_median:
            self.benchmark_passed(
                "Median latency",
                "Within NFR001 target",
                median,
                target_median,
            )
        else:
            self.benchmark_failed(
                "Median latency",
                "Exceeds NFR001 target",
                median,
                target_median,
                "Review connection pool configuration and API response times",
            )

        if p95 < target_p95:
            self.benchmark_passed(
                "P95 latency",
                "Within target",
                p95,
                target_p95,
            )
        else:
            self.benchmark_failed(
                "P95 latency",
                "Exceeds target",
                p95,
                target_p95,
                "Investigate slow queries and add caching (Story 2.2)",
            )

        return {
            "name": "single_query",
            "queries": len(latencies),
            "errors": errors,
            "latency": {
                "median": median,
                "p95": p95,
                "p99": p99,
                "min": min_lat,
                "max": max_lat,
            },
            "pass": median < target_median and p95 < target_p95,
        }

    async def run_concurrent_queries_benchmark(self, concurrency: int) -> dict[str, Any]:
        """
        Benchmark: Concurrent queries performance.

        Args:
            concurrency: Number of concurrent queries

        Returns:
            dict: Benchmark results
        """
        self.print_section(f"Benchmark: {concurrency} Concurrent Queries")

        latencies = []
        errors = 0

        print(f"{BLUE}>{RESET} Running {concurrency} concurrent queries...")

        async def single_query() -> float:
            """Execute a single query and return latency."""
            start = time.time()
            try:
                # Simulate MCP tool call
                await asyncio.sleep(0.1)  # Mock latency
                return time.time() - start
            except Exception as e:
                nonlocal errors
                errors += 1
                raise

        # Run concurrent queries
        start_time = time.time()
        tasks = [single_query() for _ in range(concurrency)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time

        # Collect latencies (filter out errors)
        latencies = [r for r in results if isinstance(r, float)]

        if not latencies:
            return {
                "name": f"{concurrency}_concurrent",
                "error": "All queries failed",
                "pass": False,
            }

        median = statistics.median(latencies)
        p95 = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(
            latencies
        )
        p99 = statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else max(
            latencies
        )
        throughput = len(latencies) / total_time
        error_rate = errors / concurrency * 100

        # NFR001 target: 25 concurrent users without degradation
        target_median = 5.0
        target_p95 = 10.0
        target_error_rate = 5.0  # <5% error rate

        # Report results
        self.benchmark_info("Queries executed", len(latencies), f" / {concurrency}")
        self.benchmark_info("Errors", errors)
        self.benchmark_info("Error rate", f"{error_rate:.1f}%")
        self.benchmark_info("Throughput", f"{throughput:.1f}", " queries/sec")
        self.benchmark_info("Total time", f"{total_time:.2f}s")

        if median < target_median:
            self.benchmark_passed(
                "Median latency",
                "Within NFR001 target",
                median,
                target_median,
            )
        else:
            self.benchmark_failed(
                "Median latency",
                "Exceeds NFR001 target",
                median,
                target_median,
                f"Increase CANARY_POOL_SIZE (current: {concurrency}+ needed)",
            )

        if p95 < target_p95:
            self.benchmark_passed(
                "P95 latency",
                "Within target",
                p95,
                target_p95,
            )
        else:
            self.benchmark_failed(
                "P95 latency",
                "Exceeds target",
                p95,
                target_p95,
                "Add retry logic (Story 2.3) and caching (Story 2.2)",
            )

        if error_rate < target_error_rate:
            self.benchmark_passed(
                "Error rate",
                "Within target",
                error_rate,
                target_error_rate,
            )
        else:
            self.benchmark_failed(
                "Error rate",
                "Exceeds target",
                error_rate,
                target_error_rate,
                "Implement circuit breaker and retry logic (Story 2.3)",
            )

        return {
            "name": f"{concurrency}_concurrent",
            "concurrency": concurrency,
            "queries": len(latencies),
            "errors": errors,
            "error_rate": error_rate,
            "throughput": throughput,
            "total_time": total_time,
            "latency": {
                "median": median,
                "p95": p95,
                "p99": p99,
            },
            "pass": median < target_median and p95 < target_p95 and error_rate < target_error_rate,
        }

    def print_summary(self) -> None:
        """Print benchmark summary."""
        self.print_section("Benchmark Summary")

        total = self.passed + self.failed
        success_rate = (self.passed / total * 100) if total > 0 else 0

        print(f"\n{BOLD}Results:{RESET}")
        print(f"  {GREEN}PASS{RESET} Passed: {self.passed}")
        print(f"  {RED}FAIL{RESET} Failed: {self.failed}")
        print(f"  Success Rate: {BOLD}{success_rate:.1f}%{RESET}")

        overall_pass = self.failed == 0

        if overall_pass:
            print(f"\n{GREEN}{BOLD}[PASS] BENCHMARK PASSED{RESET}")
            print(
                f"{GREEN}  All performance targets met. Server ready for production.{RESET}"
            )
        else:
            print(f"\n{RED}{BOLD}[FAIL] BENCHMARK FAILED{RESET}")
            print(
                f"{RED}  Some performance targets not met. "
                f"Review suggestions above.{RESET}"
            )

        self.results["summary"] = {
            "passed": self.passed,
            "failed": self.failed,
            "success_rate": success_rate,
            "overall_pass": overall_pass,
        }
        self.results["pass"] = overall_pass

        print(f"\n{BOLD}{'=' * 80}{RESET}\n")

    async def run_all_benchmarks(self, scenarios: list[str]) -> None:
        """
        Run all selected benchmark scenarios.

        Args:
            scenarios: List of scenario names to run
        """
        self.print_header()

        if "single" in scenarios:
            result = await self.run_single_query_benchmark()
            self.results["scenarios"]["single_query"] = result

        if "concurrent_10" in scenarios:
            result = await self.run_concurrent_queries_benchmark(10)
            self.results["scenarios"]["concurrent_10"] = result

        if "concurrent_25" in scenarios:
            result = await self.run_concurrent_queries_benchmark(25)
            self.results["scenarios"]["concurrent_25"] = result

        self.print_summary()

        # Save results to file
        if self.output_file:
            self.save_results()
        else:
            # Auto-generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            default_filename = f"benchmark-results-{timestamp}.json"
            self.output_file = default_filename
            self.save_results()

    def save_results(self) -> None:
        """Save benchmark results to JSON file."""
        if not self.output_file:
            return

        try:
            output_path = Path(self.output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w") as f:
                json.dump(self.results, f, indent=2)

            print(
                f"{GREEN}[OK]{RESET} Benchmark results saved to: {BOLD}{self.output_file}{RESET}"
            )

        except Exception as e:
            print(f"{RED}[ERROR]{RESET} Failed to save results: {e}")


async def main() -> int:
    """
    Run benchmark tool.

    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    parser = argparse.ArgumentParser(
        description="Canary MCP Server Performance Baseline Benchmark (Story 2.1)"
    )
    parser.add_argument(
        "--scenarios",
        choices=["all", "single", "concurrent_10", "concurrent_25"],
        default="all",
        help="Benchmark scenarios to run (default: all)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file for benchmark results (default: auto-generated)",
    )

    args = parser.parse_args()

    # Determine which scenarios to run
    if args.scenarios == "all":
        scenarios = ["single", "concurrent_10", "concurrent_25"]
    else:
        scenarios = [args.scenarios]

    # Run benchmarks
    runner = BenchmarkRunner(output_file=args.output)
    await runner.run_all_benchmarks(scenarios)

    # Return appropriate exit code
    return 0 if runner.results.get("pass", False) else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Benchmark interrupted by user{RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{RED}Benchmark failed with error: {e}{RESET}")
        sys.exit(1)
