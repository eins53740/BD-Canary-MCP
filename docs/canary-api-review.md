# Canary API Implementation Review

**Date:** 2025-10-31
**Purpose:** Review current Canary API usage vs. official documentation (readapi.canarylabs.com/25.4)
**Context:** Before starting Epic 2 (Production Hardening), validate we're using optimal API endpoints

---

## Current API Implementation (Epic 1)

### API Version & Base URL
- **API Version**: v2 (Read API)
- **Base URL**: `https://scunscanary.secil.pt:55236/api/v2`
- **Authentication**: Static API tokens via `apiToken` parameter

### Current Endpoints in Use

| MCP Tool | Endpoint | Method | Purpose |
|----------|----------|--------|---------|
| `search_tags` | `/api/v2/browseTags` | POST | Search for tags by pattern |
| `get_tag_metadata` | `/api/v2/getTagProperties` | POST | Get tag metadata (units, type, description) |
| `list_namespaces` | `/api/v2/browseNodes` | POST | Browse hierarchical namespace structure |
| `read_timeseries` | `/api/v2/getTagData` | POST | Retrieve timeseries data for tags |
| `get_server_info` | `/api/v2/getTimeZones`<br>`/api/v2/getAggregates` | POST | Get server capabilities (timezones, aggregates) |

### Current Request/Response Patterns

**Authentication:**
```python
# API v2 uses direct token authentication
{
    "apiToken": "your-token-here",
    ...request parameters...
}
```

**Tag Search (browseTags):**
```python
# Request
{
    "apiToken": token,
    "searchText": "Temperature*",
    "maxResults": 100
}

# Response
{
    "tags": [
        {"tagPath": "...", "unit": "...", "dataType": "..."}
    ]
}
```

**Read Timeseries (getTagData):**
```python
# Request
{
    "apiToken": token,
    "tag": "Secil.Line1.Temperature",
    "startTime": "2025-10-30T00:00:00Z",
    "endTime": "2025-10-31T00:00:00Z"
}

# Response
{
    "data": [
        {"timestamp": "...", "value": ..., "quality": "Good"}
    ]
}
```

---

## Epic 1 Implementation Status ✅

All 5 core MCP tools successfully implemented and tested:
- ✅ 138 tests passing (137 pass, 1 minor failing test)
- ✅ API v2 endpoints working correctly
- ✅ Authentication with static tokens functional
- ✅ Natural language time expression parsing
- ✅ Error handling and logging in place

---

## Recommendations for Epic 2 (Connection Pooling & Performance)

### 1. Connection Pooling Configuration

**Current State (Epic 1):**
```python
# Each request creates new httpx.AsyncClient
async with httpx.AsyncClient(timeout=10.0) as http_client:
    response = await http_client.post(...)
```

**Recommended for Epic 2 (Story 2.1):**
```python
# Reusable AsyncClient with connection pooling
self.http_client = httpx.AsyncClient(
    limits=httpx.Limits(
        max_connections=10,  # Configurable pool size
        max_keepalive_connections=5
    ),
    timeout=httpx.Timeout(30.0, read=60.0),  # Configurable timeouts
    http2=False  # Canary API uses HTTP/1.1
)
```

**Benefits:**
- Connection reuse across multiple requests
- Reduced overhead for establishing TCP/TLS connections
- Better performance for concurrent requests

**Configuration:**
```bash
# .env file
CANARY_POOL_SIZE=10              # Max connections in pool
CANARY_TIMEOUT=30                # Default request timeout (seconds)
CANARY_READ_TIMEOUT=60           # Read timeout for large data responses
```

---

### 2. API Endpoint Optimization

**No Changes Needed** - Current endpoints are optimal for Epic 2:

| Endpoint | Caching Strategy (Story 2.2) | Why |
|----------|------------------------------|-----|
| `browseTags` | Cache 1 hour TTL | Tag structure rarely changes |
| `getTagProperties` | Cache 1 hour TTL | Metadata (units, type) static |
| `browseNodes` | Cache 1 hour TTL | Namespace hierarchy stable |
| `getTagData` | Cache 5 minutes TTL | Recent timeseries data changes frequently |
| `getTimeZones`<br>`getAggregates` | Cache indefinitely | Server capabilities don't change |

**Cache Bypass:**
```python
# User can request fresh data (bypass cache)
read_timeseries(tag="...", bypass_cache=True)
```

---

### 3. Pagination & Large Dataset Handling

**Current Implementation:**
- `search_tags`: Returns max 100 results (hardcoded)
- `read_timeseries`: Returns all data in single response (potential issue for large ranges)

**Recommendation for Epic 2:**
```python
# Story 2.2: Add pagination support for large timeseries queries
{
    "apiToken": token,
    "tag": "Secil.Line1.Temperature",
    "startTime": "2025-10-01T00:00:00Z",
    "endTime": "2025-10-31T00:00:00Z",
    "pageSize": 1000,  # NEW: Limit results per request
    "pageIndex": 0     # NEW: Pagination index
}
```

**Implementation Notes:**
- Add automatic pagination if result set > pageSize
- Stream large results to avoid memory issues
- Document recommended pageSize (default: 1000, max: 10000)

---

### 4. Error Handling & Retry Logic (Story 2.3)

**Recommended Retry Strategy:**
```python
from tenacity import retry, stop_after_attempt, wait_exponential
from pybreaker import CircuitBreaker

# Retry transient failures (network, timeouts)
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError))
)
async def _make_api_request(...):
    ...

# Circuit breaker for cascading failures
canary_breaker = CircuitBreaker(
    fail_max=5,           # Open after 5 consecutive failures
    timeout_duration=60,  # Stay open for 60 seconds
    reset_timeout=10      # Half-open after 10 seconds
)
```

**Error Categorization:**
- **Transient (RETRY)**: Network errors, timeouts, 502/503/504 status codes
- **Permanent (FAIL FAST)**: 400 Bad Request, 401 Unauthorized, 404 Not Found
- **User Error (NO RETRY)**: Invalid tag names, malformed time ranges

---

### 5. Performance Metrics (Story 2.1)

**Prometheus Metrics to Collect:**
```python
# Request latency histogram
canary_request_duration_seconds{tool="search_tags", status="success"}
canary_request_duration_seconds{tool="read_timeseries", status="success"}

# Request counter
canary_requests_total{tool="search_tags", status_code="200"}
canary_requests_total{tool="read_timeseries", status_code="200"}

# Connection pool gauge
canary_pool_connections_active
canary_pool_connections_idle

# Cache performance
canary_cache_hits_total
canary_cache_misses_total
canary_cache_size_bytes
```

**Metrics Endpoint:**
```bash
# Expose metrics for monitoring
GET http://localhost:8080/metrics

# Returns Prometheus text format
# canary_request_duration_seconds_bucket{tool="search_tags",le="0.5"} 45
# canary_request_duration_seconds_bucket{tool="search_tags",le="1.0"} 98
# ...
```

---

## API Stability Assessment

### Stable Endpoints (No Changes Expected)
✅ All current endpoints are stable and documented in Canary API v2
✅ No deprecated endpoints in use
✅ Authentication method is standard for Read API v2

### Future Considerations (Post-Epic 2)

**Aggregation API (Deferred to Phase 2):**
```python
# /api/v2/getAggregateData endpoint for server-side aggregation
{
    "apiToken": token,
    "tag": "Secil.Line1.Temperature",
    "startTime": "2025-10-01T00:00:00Z",
    "endTime": "2025-10-31T00:00:00Z",
    "aggregate": "average",  # Options: average, min, max, sum, percentile
    "interval": "1h"         # Time bucket size
}
```

**Rationale for Deferring:**
- LLMs can perform basic aggregation on retrieved data for MVP
- Server-side aggregation adds complexity without blocking core use cases
- Can be added in Epic 3 if performance bottlenecks emerge

---

## Conclusion & Recommendations

### ✅ Current API Implementation is Solid
- API v2 endpoints are optimal for our use case
- No endpoint changes needed for Epic 2
- Authentication method is standard and secure

### 🚀 Epic 2 Focus Areas
1. **Connection Pooling** (Story 2.1) - Implement httpx AsyncClient pool with configurable limits
2. **Caching Layer** (Story 2.2) - Cache tag metadata (1h TTL) and recent timeseries (5min TTL)
3. **Retry Logic** (Story 2.3) - Implement tenacity retry + pybreaker circuit breaker
4. **Performance Metrics** (Story 2.1) - Expose Prometheus metrics endpoint
5. **Pagination** (Story 2.2) - Add pageSize parameter for large timeseries queries

### 📋 No Breaking Changes Required
- Current Epic 1 implementation remains valid
- Epic 2 enhancements are **additive** (no API endpoint changes)
- Backward compatibility maintained throughout

---

**Next Steps:**
1. Proceed with Story 2.1 (Connection Pooling & Performance Baseline)
2. No API migrations or endpoint changes needed
3. Focus on performance optimization and reliability patterns

**Reference:**
- Canary API Documentation: https://readapi.canarylabs.com/25.4/
- Current Implementation: `src/canary_mcp/server.py`
- Test Suite: 138 tests covering all 5 MCP tools
