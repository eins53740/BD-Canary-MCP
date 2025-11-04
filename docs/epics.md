# BD-hackaton-2025-10 - Epic Breakdown

**Author:** BD
**Date:** 2025-10-30
**Project Level:** 2
**Target Scale:** 15-19 stories across 2 epics

---

## Overview

This document provides the detailed epic breakdown for BD-hackaton-2025-10 (Universal Canary MCP Server), expanding on the high-level epic list in the [PRD](./PRD.md).

Each epic includes:

- Expanded goal and value proposition
- Complete story breakdown with user stories
- Acceptance criteria for each story
- Story sequencing and dependencies

**Epic Sequencing Principles:**

- Epic 1 establishes foundational MCP server with 5 core tools and validation
- Epic 2 builds progressively, adding production reliability and performance
- Stories within epics are vertically sliced and sequentially ordered
- No forward dependencies - each story builds only on previous work
- Each story includes user-runnable validation tests

---

## Epic 1: Core MCP Server & Data Access

**Estimated Stories:** 11 stories

**Goal:** Establish production-ready MCP server with 5 core tools (list_namespaces, search_tags, get_tag_metadata, read_timeseries, get_server_info) enabling basic plant data queries through LLM interfaces, with validation test scripts for each capability.

**Epic Completion Criteria:** User can run validation test suite that demonstrates all 5 MCP tools working against live Canary API with successful happy path results.

---

### Story 1.1: MCP Server Foundation & Protocol Implementation

As a **Developer**,
I want to set up the MCP server project structure with MCP protocol implementation,
So that I can build MCP tools that LLM clients can invoke.

**Acceptance Criteria:**
1. Python 3.13 project initialized with uv dependency management
2. MCP SDK (FastMCP or MCP Python SDK) integrated and configured
3. Basic MCP server starts and listens for tool calls
4. Sample "ping" tool responds successfully to test LLM client connection
5. Project structure follows best practices (src/, tests/, docs/, config/)
6. README with project overview and architecture diagram
7. Validation test: `test_mcp_server_startup.py` confirms server starts and accepts tool calls

**Prerequisites:** None (foundational story)

---

### Story 1.2: Canary API Authentication & Session Management

As a **UNS Developer**,
I want the MCP server to authenticate with Canary Views Web API and manage session tokens,
So that all subsequent tools can securely access plant data.

**Acceptance Criteria:**
1. Canary API authentication implemented using token-based auth
2. Session token management with automatic refresh before expiry
3. Credentials loaded from environment variables (CANARY_API_URL, CANARY_API_TOKEN)
4. Connection retry logic with exponential backoff (3 attempts)
5. Clear error messages for authentication failures
6. Configuration validation tool verifies connection before server starts
7. Validation test: `test_canary_auth.py` confirms successful authentication and token refresh

**Prerequisites:** Story 1.1 (MCP server foundation)

---

### Story 1.3: list_namespaces Tool & Validation

As a **UNS Developer**,
I want to discover available namespaces in Canary Historian through an MCP tool,
So that I can understand the plant data structure and verify namespace configuration.

**Acceptance Criteria:**
1. `list_namespaces` MCP tool implemented
2. Tool returns hierarchical list of sites, assets, and namespaces from Canary
3. Tool accepts optional depth parameter to control hierarchy levels
4. Response includes namespace paths (e.g., "Maceira.Cement.Kiln6")
5. Empty namespace handling with clear messaging
6. Error handling for Canary API failures
7. Validation test: `test_list_namespaces.py` confirms namespaces retrieved from test Canary instance

**Prerequisites:** Story 1.2 (Canary API authentication)

---

### Story 1.4: search_tags Tool & Validation

As a **Plant Engineer**,
I want to search for tags by name/regex with metadata filters,
So that I can find relevant sensor data without knowing exact tag names.

**Acceptance Criteria:**
1. `search_tags` MCP tool implemented
2. Tool accepts search query (name/regex pattern)
3. Tool accepts optional filters: namespace, unit type, data type
4. Returns list of matching tags with basic metadata (name, unit, type)
5. Supports partial matching and case-insensitive search
6. Handles no matches gracefully with helpful suggestions
7. Response limited to 100 tags with pagination support
8. Validation test: `test_search_tags.py` confirms tag search with various patterns and filters

**Prerequisites:** Story 1.3 (list_namespaces tool)

---

### Story 1.5: get_tag_metadata Tool & Validation

As a **Data Analyst**,
I want to retrieve detailed metadata for specific tags,
So that I understand tag properties (units, data type, ranges) before querying timeseries data.

**Acceptance Criteria:**
1. `get_tag_metadata` MCP tool implemented
2. Tool accepts single tag name or list of tag names
3. Returns comprehensive metadata: units, data type, description, min/max values, sampling mode
4. Handles missing tags with clear error messages
5. Response format optimized for LLM interpretation
6. Bulk metadata retrieval for multiple tags in single call
7. Validation test: `test_get_tag_metadata.py` confirms metadata retrieval for known test tags

**Prerequisites:** Story 1.4 (search_tags tool)

---

### Story 1.6: read_timeseries Tool & Validation

As a **Plant Engineer**,
I want to retrieve historical timeseries data for specific tags and time ranges,
So that I can analyze plant performance and troubleshoot operational issues.

**Acceptance Criteria:**
1. `read_timeseries` MCP tool implemented
2. Tool accepts: tag name(s), start time, end time
3. Tool supports natural language time expressions ("last week", "yesterday", "past 24 hours") via FR014
4. Returns timeseries data: timestamps, values, quality flags
5. Paging support for large result sets (configurable page size, default 1000 samples)
6. Empty result handling: distinguishes "no data available" vs "tag not found" (FR020)
7. Data quality flags surfaced in response (FR025)
8. Response format structured for LLM analysis
9. Validation test: `test_read_timeseries.py` confirms data retrieval with various time ranges and quality scenarios

**Prerequisites:** Story 1.5 (get_tag_metadata tool)

---

### Story 1.7: get_server_info Tool & Validation

As a **UNS Developer**,
I want to check Canary server health and capabilities,
So that I can verify the MCP server is connected and understand available features.

**Acceptance Criteria:**
1. `get_server_info` MCP tool implemented
2. Returns Canary server version, status, and health information
3. Returns supported time zones and aggregation functions
4. Returns MCP server version and configuration details
5. HTTP health check endpoint `/health` for container orchestration
6. Health check returns JSON with status and connection state
7. Validation test: `test_server_info.py` confirms health check and server info retrieval

**Prerequisites:** Story 1.2 (Canary API authentication)

---

### Story 1.8: Test Data Fixtures & Mock Responses

As a **Developer**,
I want test data fixtures and mock Canary API responses,
So that I can develop and test offline without requiring live Canary connection.

**Acceptance Criteria:**
1. Test fixtures created for all 5 MCP tools (sample requests/responses)
2. Mock Canary API responses for common scenarios
3. Test data includes: namespaces, tags, metadata, timeseries samples
4. Mock error scenarios: authentication failures, missing tags, empty results
5. pytest fixtures configured for easy test reuse
6. Documentation on using test fixtures for development
7. Validation test: `test_mock_responses.py` confirms all fixtures load and validate correctly

**Prerequisites:** Stories 1.3-1.7 (all 5 MCP tools implemented)

---

### Story 1.9: Basic Error Handling & Logging

As a **UNS Developer**,
I want structured logging and clear error messages,
So that I can troubleshoot issues and understand MCP server behavior.

**Acceptance Criteria:**
1. Structured JSON logging implemented (timestamp, level, message, context)
2. Log levels configurable via environment variable (DEBUG, INFO, WARN, ERROR)
3. All MCP tool calls logged with request/response details
4. Error messages optimized for both LLMs and humans (FR009)
5. Query transparency: log which tags were queried and why (FR021)
6. Request ID tracking for correlation across log entries
7. Log rotation configured for production use
8. Validation test: `test_logging.py` confirms log output format and error message clarity

**Prerequisites:** Stories 1.3-1.7 (all 5 MCP tools implemented)

---

### Story 1.10: Non-Admin User Installation & Docker Alternative

As a **Basic Windows PC User**,
I want to install and run the MCP server without administrator privileges,
So that I can use the tool on my company workstation without IT assistance.

**Acceptance Criteria:**

**Primary Path (Non-Admin Installation):**
1. Installation guide for non-admin Windows users (user-space Python)
2. Python 3.13 portable installation instructions (no admin required)
3. MCP server installs via pip/uv to user directory (`%USERPROFILE%\.local` or similar)
4. Server runs as regular user process (no admin/elevated privileges needed)
5. Configuration via environment variables or user config file in home directory
6. Installation validation script confirms setup without requiring admin rights
7. Troubleshooting guide for common non-admin installation issues

**Alternative Path (Docker for Admin Sessions):**
8. Dockerfile for containerized deployment
9. Docker Compose configuration with environment variable injection
10. Docker installation guide for users with admin/Docker access
11. Container runs with non-root user inside Docker

**Common Requirements:**
12. Both installation paths use identical configuration format
13. README clearly documents both installation options and when to use each
14. Validation test: `test_installation.py` confirms both installation methods work correctly

**Prerequisites:** Stories 1.1-1.9 (complete MCP server with all tools)

---

### Story 1.11: Local Development Environment & Setup Validation

As a **Developer**,
I want a streamlined local development environment with setup validation,
So that I can quickly start developing and testing MCP server enhancements.

**Acceptance Criteria:**
1. Development environment setup guide (Python, uv, dependencies)
2. Pre-commit hooks configured (Ruff linting, formatting)
3. VS Code / IDE configuration recommendations
4. Environment variable template (`.env.example`) with documentation
5. Development mode with hot-reload for rapid iteration
6. Setup validation script confirms: dependencies installed, config valid, tests pass
7. Developer quick-start guide (<5 minutes to running server)
8. Validation test: `test_dev_environment.py` confirms dev setup is complete and functional

**Prerequisites:** Story 1.10 (installation methods)

---

**Epic 1 Complete!** All 11 stories deliver a production-ready MCP server with 5 core tools, comprehensive validation tests, and flexible installation options for both non-admin and admin users.

---

## Epic 2: Production Hardening & User Enablement

**Estimated Stories:** 8 stories

**Goal:** Add production-grade reliability, performance optimization (caching, connection pooling), comprehensive documentation, and deployment automation with performance validation to support 6-site rollout.

**Epic Completion Criteria:** User can run performance validation script that confirms <5s median query response time and error handling with retry logic demonstrates resilience.

---

### Story 2.1: Connection Pooling & Performance Baseline

As a **UNS Developer**,
I want connection pooling to Canary API and performance baseline metrics,
So that the MCP server handles concurrent requests efficiently and I can measure performance improvements.

**Acceptance Criteria:**
1. HTTP connection pool implemented for Canary API (configurable pool size, default 10 connections)
2. Connection reuse across multiple requests to same Canary instance
3. Connection timeout configuration (default 30s per request)
4. Performance metrics collection: request latency, API response times, cache hit/miss rates
5. Metrics endpoint `/metrics` in Prometheus format
6. Baseline performance benchmarking tool that measures current performance
7. Benchmark report shows: median latency, p95/p99 latency, throughput
8. Validation test: `test_connection_pool.py` confirms pool reuses connections and handles concurrent requests

**Prerequisites:** Epic 1 complete (all 11 stories)

---

### Story 2.2: Caching Layer Implementation

As a **Plant Engineer**,
I want frequently accessed data cached locally,
So that I get faster query responses and reduce load on Canary API.

**Acceptance Criteria:**
1. Caching layer implemented using SQLite for local deployment
2. Tag metadata cached with configurable TTL (default 1 hour)
3. Timeseries data cached for recent queries (last 24 hours) with TTL (default 5 minutes)
4. Cache key strategy: namespace + tag + time range hash
5. Cache hit/miss logging for observability
6. Cache bypass option via tool parameter for fresh data requests (FR026)
7. Cache invalidation on configuration changes
8. Cache size limits with LRU eviction policy (default 100MB)
9. Performance improvement: queries achieve <5s median response time (NFR001)
10. Validation test: `test_caching.py` confirms cache hits reduce query time and cache bypasses work correctly

**Prerequisites:** Story 2.1 (connection pooling and baseline metrics)

---

### Story 2.3: Advanced Error Handling & Retry Logic

As a **UNS Developer**,
I want robust error handling with retry logic and circuit breaker,
So that the MCP server automatically recovers from transient failures and protects Canary API from cascading failures.

**Acceptance Criteria:**
1. Retry logic with exponential backoff implemented (3-5 retries, configurable)
2. Backoff strategy: initial 1s, then 2s, 4s, 8s with jitter to prevent thundering herd
3. Circuit breaker pattern: opens after 5 consecutive failures, auto-recovers after 60s cooldown
4. Graceful degradation: return cached data when Canary API unavailable with clear messaging
5. Error categorization: transient (retry), permanent (fail fast), user error (no retry)
6. Enhanced error messages for LLMs and humans with remediation steps
7. Circuit breaker state exposed via `/health` endpoint
8. Metrics tracking: retry attempts, circuit breaker state changes, error rates
9. Validation test: `test_error_handling.py` simulates API failures and confirms retry/circuit breaker behavior

**Prerequisites:** Story 2.2 (caching layer for graceful degradation)

---

### Story 2.4: Performance Validation Test Suite

As a **UNS Developer**,
I want automated performance validation tests,
So that I can verify the MCP server meets <5s response time requirements before site deployment.

**Acceptance Criteria:**
1. Performance test suite implemented with automated benchmarking
2. Test scenarios: single query, concurrent queries (10 users), high load (25 users)
3. Tests measure: median latency, p95/p99 latency, throughput, error rates
4. Pass/fail criteria: median <5s, p95 <10s, 95%+ success rate (NFR001)
5. Performance test runs against test Canary instance or mocks
6. Benchmark comparison: before/after optimization (vs Story 2.1 baseline)
7. Test report generated: summary statistics, performance graphs, pass/fail status
8. CI/CD integration: performance tests run on every build
9. Validation test: `test_performance_suite.py` confirms all performance tests pass

**Prerequisites:** Stories 2.1-2.3 (performance optimizations complete)

---

### Story 2.5: Multi-Site Configuration Management

As a **UNS Developer**,
I want to manage configuration for multiple Canary sites,
So that I can easily deploy the MCP server to all 6 sites with site-specific settings.

**Acceptance Criteria:**
1. Multi-site configuration via config file (YAML or JSON)
2. Config structure: array of site configs with name, URL, credentials, settings
3. Site selection via environment variable or CLI parameter
4. Config validation on startup: checks all sites have required fields
5. Config templates for common deployment scenarios
6. Support for site-specific overrides (timeouts, cache TTL, connection pool size)
7. Secure credential management: environment variables take precedence over config file
8. Configuration documentation with examples for 6-site deployment
9. Validation test: `test_multisite_config.py` confirms config loading and site switching

**Prerequisites:** Story 2.3 (advanced error handling)

---

### Story 2.6: API Documentation Generation

As a **Phase 2 User (Plant Engineer)**,
I want comprehensive API documentation for all MCP tools,
So that I can understand available tools and how to use them without developer assistance.

**Acceptance Criteria:**
1. API documentation auto-generated from MCP tool definitions
2. Documentation includes: tool name, description, parameters, return types, examples
3. Documentation format: Markdown for human reading, JSON schema for tooling
4. Each tool documented with: purpose, use cases, parameter details, response format
5. Error codes and troubleshooting guide included
6. Documentation published to docs/ folder and README
7. Examples show real Canary queries for common use cases
8. Documentation versioned with MCP server releases
9. Validation test: `test_documentation.py` confirms docs generated and complete

**Prerequisites:** Story 2.5 (multi-site configuration)

---

### Story 2.7: Example Query Library & Use Cases

As a **Plant Engineer**,
I want a library of example queries for common plant data analysis scenarios,
So that I can quickly learn how to use the MCP server for my daily tasks.

**Acceptance Criteria:**
1. Example query library created with 15-20 common use cases
2. Examples cover: temperature trends, cross-tag comparisons, anomaly detection, quality issues
3. Each example includes: natural language query, expected MCP tool calls, sample response
4. Examples organized by use case category: validation, troubleshooting, optimization, reporting
5. Examples include queries for all 5 MCP tools
6. Interactive examples: users can copy/paste into Claude Desktop
7. Examples reference real-world scenarios from Product Brief (Kiln 6, Maceira plant, etc.)
8. Example library published in docs/ and README
9. Include integration example comparing historical vs recent data (e.g., "Compare Kiln 6 temperature: last week average vs last minute value")
10. Validation test: `test_examples.py` confirms all example queries are valid and return expected results

**Prerequisites:** Story 2.6 (API documentation)

---

### Story 2.8: Deployment Guide & Site Rollout Documentation

As a **UNS Developer**,
I want step-by-step deployment instructions for site rollout,
So that I can deploy the MCP server to all 6 Canary sites consistently and efficiently.

**Acceptance Criteria:**
1. Deployment guide covering both installation paths (non-admin and Docker)
2. Step-by-step instructions for each site deployment phase:
   - Pre-deployment checklist
   - Installation steps
   - Configuration setup
   - Connection validation
   - Performance verification
   - User onboarding
3. Site-specific configuration examples for 6-site rollout
4. Deployment validation checklist (mirrors Epic completion criteria)
5. Troubleshooting guide for common deployment issues
6. Rollback procedures if deployment fails
7. Post-deployment monitoring recommendations
8. User onboarding guide for Phase 2 users (plant engineers, analysts)
9. Deployment timeline estimation (<30 minutes per site)
10. Validation test: `test_deployment_guide.py` confirms documentation completeness

**Prerequisites:** Stories 2.1-2.7 (all production features and documentation complete)

---

**Epic 2 Complete!** All 8 stories deliver production-hardened MCP server with performance optimization, comprehensive documentation, and deployment guidance for 6-site rollout.

---

## Story Guidelines Reference

**Story Format:**

```
**Story [EPIC.N]: [Story Title]**

As a [user type],
I want [goal/desire],
So that [benefit/value].

**Acceptance Criteria:**
1. [Specific testable criterion]
2. [Another specific criterion]
3. [etc.]

**Prerequisites:** [Dependencies on previous stories, if any]
```

**Story Requirements:**

- **Vertical slices** - Complete, testable functionality delivery
- **Sequential ordering** - Logical progression within epic
- **No forward dependencies** - Only depend on previous work
- **AI-agent sized** - Completable in 2-4 hour focused session
- **Value-focused** - Integrate technical enablers into value-delivering stories
- **User-testable** - Each story includes runnable validation tests

---

**For implementation:** Use the `create-story` workflow to generate individual story implementation plans from this epic breakdown.

---

## Epic 3: Semantic Tag Search

**Estimated Stories:** 5 stories

**Goal:** Introduce a new "get_tag_path" MCP tool that uses natural language processing to find the most likely tag path from a user's descriptive query, making the server more intuitive and user-friendly.

**Epic Completion Criteria:** A user can provide a natural language query like "average temperature for the kiln shell in section 15" to the `get_tag_path` tool and receive the correct, full tag path as a result.

---

### Story 3.1: `get_tag_path` Tool Foundation

As a **Plant Engineer**,
I want a new MCP tool called `get_tag_path` that accepts a natural language description,
So that I can start the process of finding a tag without knowing any part of its path.

**Acceptance Criteria:**
1. New `get_tag_path` MCP tool is created in `server.py`.
2. Tool accepts a single string argument `description`.
3. The tool performs an initial search using the existing `search_tags` logic.
4. The tool extracts and cleans keywords from the input description (e.g., removes stop words).
5. A basic list of candidate tags is returned if any are found.
6. Validation test: `test_get_tag_path_foundation.py` confirms the tool can be called and returns initial candidates.

**Prerequisites:** Epic 1 complete.

---

### Story 3.2: Tag Ranking and Scoring Algorithm

As a **Data Analyst**,
I want the `get_tag_path` tool to intelligently rank search results,
So that the most relevant tag is presented first.

**Acceptance Criteria:**
1. A scoring algorithm is implemented within the `get_tag_path` tool.
2. The algorithm calculates a relevance score for each candidate tag.
3. Scoring is weighted, prioritizing keywords found in the tag's `name` over its `path`.
4. The candidate list returned by the tool is sorted by this score in descending order.
5. The top-scoring tag is identified as the `most_likely_path` in the response.
6. Validation test: `test_tag_scoring.py` confirms that known tags are scored and ranked correctly based on test queries.

**Prerequisites:** Story 3.1

---

### Story 3.3: Integration with `getTagProperties`

As a **Data Analyst**,
I want the `get_tag_path` tool to use a tag's full metadata in its ranking,
So that the search is more accurate by considering the tag's description and other properties.

**Acceptance Criteria:**
1. The `get_tag_path` tool now calls the `get_tag_metadata` logic for each candidate tag.
2. The scoring algorithm is enhanced to include the tag's `description` and other relevant metadata fields.
3. Keywords found in the description add to the tag's relevance score (with a lower weight than name or path).
4. The tool's response includes the description of the top candidates to provide more context to the user.
5. Validation test: `test_metadata_integration.py` confirms that a tag's description influences its final score.

**Prerequisites:** Story 3.2

---

### Story 3.4: Caching Strategy for `get_tag_path`

As a **Developer**,
I want the `get_tag_path` tool to cache its results,
So that repeated queries are faster and the load on the Canary API is reduced.

**Acceptance Criteria:**
1. The `get_tag_path` tool is integrated with the existing caching store (`get_cache_store()`)
2. Intermediate API calls (`browseTags`, `getTagProperties`) made within the tool are cached.
3. The final ranked result of a `get_tag_path` query is itself cached.
4. The cache can be bypassed with a `bypass_cache` parameter in the tool.
5. Cache hit/miss rates for this tool are added to the server's metrics.
6. Validation test: `test_get_tag_path_caching.py` confirms that repeated calls are served from the cache and that the bypass works.

**Prerequisites:** Story 3.3, Story 2.2 (Caching Layer Implementation)

---

### Story 3.5: Tool Validation and Testing

As a **Developer**,
I want a comprehensive set of tests for the `get_tag_path` tool,
So that I can ensure its accuracy, performance, and reliability.

**Acceptance Criteria:**
1. Unit tests are created for the scoring algorithm, testing various keyword combinations.
2. Integration tests are created to validate the entire `get_tag_path` workflow with mock API responses.
3. An end-to-end validation test (`test_get_tag_path.py`) is created to run against a live (or mocked) Canary instance.
4. The test suite includes scenarios with no matches, one match, and multiple matches.
5. All new code is included in the project's test coverage.

**Prerequisites:** Story 3.4

---

**Epic 3 Complete!** All 5 stories deliver a powerful, user-friendly semantic search tool that makes finding tags in the Canary Historian more intuitive.

