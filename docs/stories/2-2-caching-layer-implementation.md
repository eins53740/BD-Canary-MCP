# Story 2.2: Caching Layer Implementation

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
