# Story 2.3: Advanced Error Handling & Retry Logic

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
