# Story 2.1: Connection Pooling & Performance Baseline

Status: drafted

## Story

As a **UNS Developer**,
I want connection pooling to Canary API and performance baseline metrics,
So that the MCP server handles concurrent requests efficiently and I can measure performance improvements.

## Acceptance Criteria

1. HTTP connection pool implemented for Canary API (configurable pool size, default 10 connections)
2. Connection reuse across multiple requests to same Canary instance
3. Connection timeout configuration (default 30s per request)
4. Performance metrics collection: request latency, API response times, cache hit/miss rates
5. Metrics endpoint `/metrics` in Prometheus format
6. Baseline performance benchmarking tool that measures current performance
7. Benchmark report shows: median latency, p95/p99 latency, throughput
8. Validation test: `test_connection_pool.py` confirms pool reuses connections and handles concurrent requests

## Tasks / Subtasks

- [ ] Task 1: Implement Connection Pooling in Canary Client (AC: #1, #2, #3)
  - [ ] Update `src/canary/client.py` to use httpx AsyncClient with connection pooling
  - [ ] Configure httpx connection pool with limits parameter (default max_connections=10)
  - [ ] Add connection timeout configuration (default 30s per request)
  - [ ] Ensure connection reuse across multiple requests via AsyncClient session
  - [ ] Add configuration options: CANARY_POOL_SIZE, CANARY_TIMEOUT environment variables
  - [ ] Document pool configuration in .env.example

- [ ] Task 2: Implement Performance Metrics Collection (AC: #4)
  - [ ] Add request timing middleware to Canary client
  - [ ] Track metrics: request latency (start to end), API response time, request count
  - [ ] Add cache hit/miss counters (prepare for Story 2.2 caching layer)
  - [ ] Store metrics in memory structure for metrics endpoint retrieval
  - [ ] Include per-tool metrics breakdown (list_namespaces, search_tags, etc.)

- [ ] Task 3: Create Prometheus Metrics Endpoint (AC: #5)
  - [ ] Add `/metrics` HTTP endpoint to MCP server (optional, for observability)
  - [ ] Format metrics in Prometheus text exposition format
  - [ ] Export metrics: canary_request_duration_seconds (histogram), canary_requests_total (counter), canary_pool_connections_active (gauge)
  - [ ] Include labels: tool_name, status_code, error_type
  - [ ] Document metrics endpoint in README

- [ ] Task 4: Create Baseline Performance Benchmarking Tool (AC: #6, #7)
  - [ ] Create `scripts/benchmark.py` script
  - [ ] Implement benchmark scenarios: single query, 10 concurrent queries, 25 concurrent queries
  - [ ] Measure: median latency, p95/p99 latency, throughput (queries/second), error rate
  - [ ] Generate benchmark report with summary statistics and recommendations
  - [ ] Compare against NFR001 target: <5s median query response time
  - [ ] Output benchmark results to terminal with color-coded pass/fail indicators
  - [ ] Save benchmark results to file: `benchmark-results-{timestamp}.json`

- [ ] Task 5: Create Validation Test Suite (AC: #8)
  - [ ] Create `tests/integration/test_connection_pool.py`
  - [ ] Test: connection pool reuses connections (verify single connection for sequential requests)
  - [ ] Test: pool handles concurrent requests (10 parallel queries)
  - [ ] Test: connection timeout configuration works correctly
  - [ ] Test: pool respects max_connections limit
  - [ ] Test: metrics collection tracks all requests correctly
  - [ ] Mock Canary API responses for predictable test execution

## Dev Notes

### Technical Context

**Epic Context:**
First story in Epic 2: Production Hardening & User Enablement. Establishes performance optimization foundation (connection pooling) and baseline metrics for measuring subsequent improvements (caching, error handling). Critical for achieving NFR001: <5s median query response time.

**Requirements Mapping:**
- FR016: Connection Pooling - HTTP connection pool to optimize concurrent requests
- FR010: Request Logging and Metrics - Performance metrics collection
- NFR001: Performance - <5s median query response time, 25 concurrent users without degradation
- NFR002: Reliability & Availability - Baseline metrics enable performance monitoring

**Key Technical Constraints:**
- httpx AsyncClient connection pooling must be configured at client initialization
- Connection pool size impacts memory usage and Canary API load
- Prometheus metrics format must follow official specification for monitoring tool compatibility
- Benchmark tool must not impact production server performance (run in isolated environment)

### Project Structure Notes

**Files to Create:**
- `scripts/benchmark.py` - Performance baseline benchmarking tool
- `tests/integration/test_connection_pool.py` - Connection pool validation tests

**Files to Modify:**
- `src/canary/client.py` - Add httpx AsyncClient with connection pooling configuration
- `src/canary_mcp/server.py` - Add optional /metrics endpoint for observability
- `.env.example` - Add CANARY_POOL_SIZE, CANARY_TIMEOUT configuration options
- `README.md` - Document connection pool configuration and metrics endpoint

**Architecture Alignment:**
From architecture.md:
- httpx AsyncClient with connection pooling (line 278: Epic 2, Story 2.1)
- Connection timeout configuration via httpx.Timeout
- Metrics endpoint returns Prometheus format (architecture.md line 228)
- Benchmark script location: `scripts/benchmark.py` (architecture.md line 251)

### Learnings from Previous Story

**From Story 1-11-local-development-environment-setup-validation (Status: done)**

**Validation Script Pattern (Reuse for benchmark.py):**
- Color-coded terminal output: GREEN (✓), RED (✗), YELLOW (warnings), BLUE (info)
- ANSI color codes: `\033[92m` (GREEN), `\033[91m` (RED), `\033[93m` (YELLOW), `\033[94m` (BLUE), `\033[0m` (RESET)
- Actionable error messages with fix suggestions
- Exit code 0 for success, 1 for failures
- Section headers with separators for readability
- Summary report at end with pass/fail counts

**Script Structure to Reuse:**
```python
# From validate_dev_setup.py - apply to benchmark.py
class BenchmarkRunner:
    def print_header(self): ...
    def print_section(self, title): ...
    def benchmark_passed(self, name, message): ...
    def benchmark_failed(self, name, message, suggestion): ...
    def run_all_benchmarks(self): ...
    def print_summary(self): ...
```

**Pattern Example:**
```python
# Color-coded output from Story 1-11
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

# Use for benchmark results
print(f"{GREEN}✓{RESET} Median latency: 2.3s (target: <5s)")
print(f"{RED}✗{RESET} p95 latency: 12.1s (target: <10s)")
```

**Development Environment Tools (Already Available):**
- Pre-commit hooks with Ruff linting (`.pre-commit-config.yaml`)
- VS Code configured for Python development (`.vscode/settings.json`)
- Quick-start guide for new developers (`docs/development/quick-start.md`)
- Validation script pattern established (`scripts/validate_dev_setup.py`)

**No Blocking Issues:** Story 1-11 completed without issues. All patterns ready for reuse in benchmark tool.

[Source: stories/1-11-local-development-environment-setup-validation.md#Dev-Agent-Record]

### Testing Standards

**Integration Test Requirements:**
- Test connection pool reuses connections across sequential requests
- Test concurrent request handling (10+ parallel queries)
- Test connection timeout triggers correctly
- Test pool respects max_connections limit
- Test metrics collection accuracy (request counts, latency measurements)
- Mock Canary API responses for predictable benchmark execution
- Validate Prometheus metrics format conforms to specification

**Performance Baseline Requirements:**
- Establish current performance metrics before optimizations (Story 2.1 baseline)
- Benchmark scenarios: single query, 10 concurrent, 25 concurrent
- Compare future performance against this baseline (Story 2.2 caching will improve)
- Report should clearly indicate pass/fail vs NFR001 targets

### References

- [Source: docs/epics.md#Story-2.1] - Story definition and acceptance criteria
- [Source: docs/PRD.md#FR016] - Connection pooling requirement
- [Source: docs/PRD.md#FR010] - Request logging and metrics requirement
- [Source: docs/PRD.md#NFR001] - Performance requirement (<5s median, 25 concurrent users)
- [Source: docs/architecture.md#Epic-2-Story-2.1] - httpx AsyncClient pooling, benchmark.py location
- [Source: stories/1-11-local-development-environment-setup-validation.md] - Validation script patterns

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

Sonnet 4.5 (us.anthropic.claude-sonnet-4-5-20250929-v1:0)

### Debug Log References

### Completion Notes List

### File List
