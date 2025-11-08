# Canary MCP Server API Documentation

**Story 2.6: API Documentation Generation**

Complete reference for all MCP tools provided by the Canary MCP Server.

## Table of Contents

- [Transport & Payload Guardrails](#transport--payload-guardrails)
- [Core Data Access Tools](#core-data-access-tools)
  - [search_tags](#search_tags)
  - [get_tag_path](#get_tag_path)
  - [get_tag_metadata](#get_tag_metadata)
  - [read_timeseries](#read_timeseries)
  - [get_tag_data2](#get_tag_data2)
- [get_aggregates](#get_aggregates)
- [get_asset_types](#get_asset_types)
- [get_asset_instances](#get_asset_instances)
- [get_events_limit10](#get_events_limit10)
- [browse_status](#browse_status)
- [get_tag_properties](#get_tag_properties)
  - [list_namespaces](#list_namespaces)
  - [get_server_info](#get_server_info)
  - [write_test_dataset](#write_test_dataset)
- [Performance & Monitoring Tools](#performance--monitoring-tools)
  - [get_metrics](#get_metrics)
  - [get_metrics_summary](#get_metrics_summary)
- [Cache Management Tools](#cache-management-tools)
  - [get_cache_stats](#get_cache_stats)
  - [invalidate_cache](#invalidate_cache)
  - [cleanup_expired_cache](#cleanup_expired_cache)
- [Utility Tools](#utility-tools)
  - [ping](#ping)
- [Error Codes](#error-codes)
- [Best Practices](#best-practices)

---

## Transport & Payload Guardrails

| Tool | Canary Endpoint(s) | Method | Notes |
|------|--------------------|--------|-------|
| `list_namespaces` | `/api/v2/browseNodes` | GET | Token passed via `apiToken` query parameter; no request body. |
| `search_tags` | `/api/v2/browseTags` | POST | Supports `search`, `path`, and `deep` filters in JSON payload. |
| `get_tag_metadata`, `get_tag_properties` | `/api/v2/getTagProperties` | POST | Bulk metadata lookups for one or more fully qualified tag paths. |
| `read_timeseries`, `get_last_known_values` | `/api/v2/getTagData` | POST | Complex time windows and tag lists require JSON payload. |
| `get_server_info` (time zones) | `/api/v2/getTimeZones` | GET | Lightweight catalog call; token supplied via query parameter. |
| `get_server_info` (aggregates) | `/api/v2/getAggregates` | GET | Returns supported aggregate functions; response cached on the MCP side. |

**Response Size Limit:** Every tool response is constrained to ≤1 MB (`CANARY_MAX_RESPONSE_BYTES`, default 1 000 000). When a payload would exceed the limit the server:

- logs `response_truncated` with the active `request_id` and byte counts,
- returns a compact structure containing `truncated: true`, `limit_bytes`, `original_size_bytes`, and a JSON `preview` snippet,
- advises clients to narrow time ranges, reduce tag lists, or apply additional filters before retrying.

---

## Write API Authentication

The Canary Write API utilizes tokens for authentication, which are configured within the Identity service. Each token is linked to a specific Canary user.

**Key Considerations:**

*   **Tag Security:** If Tag Security is enabled in the Identity service, the Canary user associated with the token must be granted write permissions to the appropriate DataSet(s) or local Historian view.
*   **`apiToken` Parameter:** When interacting with the Web API, the user must include the `apiToken` in their request.
*   **SaF Service Configuration:** If the Store and Forward (SaF) service used to write data is remote from the Historian, it must also be configured to use an API token. This can be the same token used in the API request.
*   **Token Creation:** For detailed instructions on generating API tokens, please refer to the Canary documentation on "How to Create an API Token."

---

## Core Data Access Tools

### search_tags

Search for Canary tags by name pattern with caching support.

**Purpose**: Discover available tags in the historian without knowing exact names.

**Parameters:**
- `search_pattern` (string, required): Tag name or pattern to search for (supports wildcards)
- `bypass_cache` (boolean, optional): Skip cache and fetch fresh data (default: false)
- `search_path` (string, optional): Namespace prefix passed to Canary `browseTags`. Defaults to the `CANARY_TAG_SEARCH_ROOT` environment variable.


**Fallbacks**: When the requested window has no samples, the tool automatically returns the latest known values (configurable via `CANARY_LAST_VALUE_LOOKBACK_HOURS`) and marks the response with `"source": "last_known"`. Tags are auto-resolved to their fully qualified paths, which are exposed via `resolved_tag_names`.
**Returns:**
```json
{
  "success": true,
  "tags": [
    {
      "name": "Kiln6.Temperature",
      "path": "Maceira.Cement.Kiln6.Temperature",
      "dataType": "float",
      "description": "Kiln 6 temperature sensor"
    }
  ],
  "count": 1,
  "pattern": "Kiln6*",
  "search_path": "Secil.Portugal",
  "cached": false,
  "hint": "Use literal identifiers (e.g. 'P431') without adding wildcard characters."
}
```

**Caching**: Results cached for 1 hour (metadata TTL)

**Path Scoping**: The tool posts to `browseTags` using the configured search path (for example `Secil.Portugal`) so queries like `"P431"` resolve correctly even within large historians. If no root path is configured, the server automatically falls back to common site prefixes.

**Hint**: Provide literal identifiers such as `"P431"` without appending wildcard characters (`*`). The Canary API performs its own partial matching and responds more reliably to the raw identifier.
**Size Guardrail**: Responses pass through the global payload guard (`CANARY_MAX_RESPONSE_BYTES`, default 1 000 000 bytes). If a result is truncated you'll receive `{"truncated": true, "preview": "..."}`—narrow the query (fewer tags, tighter namespace) and retry.

**Example Usage:**
```
User: "Find all temperature tags for Kiln 6"
Assistant uses: search_tags(search_pattern="Kiln6*Temperature")
```

**Usage Guidance:** Use `search_tags` when you already know part of the historian name (e.g., `Kiln6.Temp`). For natural-language phrases rely on `get_tag_path`, which combines the catalog, search, and metadata scoring pipeline.

**Error Handling:**
- Returns `success: false` with error message on failure
- Empty pattern returns error

---

### get_tag_path

Resolve a natural-language description into the most likely Canary tag path.

**Purpose**: Help engineers locate tags without remembering exact paths by combining search, metadata enrichment, and relevance scoring. When Canary's live search cannot find a match, the tool now consults a local index derived from `docs/aux_files/Canary_Path_description_maceira.json`, ensuring common plant terminology (for example “kiln 5 shell speed”) still yields meaningful candidates.

**Parameters:**
- `description` (string, required): Natural-language description of the desired signal.
- `max_results` (integer, optional): Number of ranked candidates to return (default: 5).
- `bypass_cache` (boolean, optional): Skip cached responses and force fresh API calls (default: false).

**Returns:**
```json
{
  "success": true,
  "description": "temperature on kiln shell in section 15",
  "keywords": ["temperature", "kiln", "shell", "section", "15"],
  "most_likely_path": "Plant.Kiln.Section15.ShellTemp",
  "alternatives": ["Plant.Kiln.Section15.ShellPressure"],
  "candidates": [
    {
      "path": "Plant.Kiln.Section15.ShellTemp",
      "name": "KilnShellTemp",
      "dataType": "float",
      "description": "Temperature sensor located on kiln shell section 15",
      "score": 18.5,
      "matched_keywords": {
        "name": ["kiln", "temperature"],
        "description": ["shell", "section"]
      },
      "search_sources": [
        "temperature kiln shell section 15",
        "temperature"
      ],
      "metadata": {
        "units": "degC",
        "properties": {
          "area": "Kiln",
          "asset": "Section15"
        }
      },
      "metadata_cached": false
    }
  ],
  "confidence": 0.91,
  "confidence_label": "high",
  "clarifying_question": null,
  "next_step": "return_path",
  "message": "High-confidence match. Proceed with read_timeseries or metadata lookup.",
  "cached": false
}
```

**Caching**: Final responses are cached with the metadata TTL. Intermediate `browseTags` and `getTagProperties` calls share the metadata cache. Use `bypass_cache=true` when fresh data is required.

**Confidence & Ranking Logic:**
- Keywords matched in the tag `name` carry the highest weight, followed by path, description, and metadata.
- Exact/prefix matches receive a bonus to break ties.
- Confidence is derived from the winning score and its margin over the runner-up:
  - `confidence ≥ 0.80` → `confidence_label = high`, `next_step = "return_path"`.
  - `0.70 ≤ confidence < 0.80` → `confidence_label = medium`, `next_step = "double_check"` (advise verifying units/section).
  - `confidence < 0.70` → the tool withholds a recommendation and asks a clarifying question.

**Example Usage:**
```
User: "What's the tag for the kiln shell temperature in section 15?"
Assistant uses: get_tag_path(description="kiln shell temperature section 15")
```

**Error Handling:**
- Empty descriptions or descriptions without meaningful keywords return `success: false`, a `clarifying_question`, and guidance (e.g., “Specify site/equipment/units”).
- When no candidates can be ranked, the response includes the top alternatives plus a clarifying question so the operator can steer the workflow.
- API or metadata failures surface actionable messages (“retry with bypass_cache”, “validate CANARY_VIEWS_BASE_URL”) instead of generic errors.

---

### get_tag_metadata

Retrieve detailed metadata for specific tags.

**Purpose**: Understand tag properties (units, data type, ranges) before querying timeseries data.

**Parameters:**
- `tag_path` (string, required): Full path or short identifier for the tag

**Returns:**
```json
{
  "success": true,
  "metadata": {
    "name": "Kiln6.Temperature",
    "path": "Maceira.Cement.Kiln6.Temperature",
    "dataType": "float",
    "units": "°C",
    "description": "Kiln 6 inlet temperature",
    "engHigh": "1500",
    "engLow": "0",
    "updateRate": "1s",
    "properties": {
      "Description": "Kiln 6 inlet temperature",
      "Units": "°C",
      "Default High Scale": "1500",
      "Default Low Scale": "0"
    }
  },
  "tag_path": "Kiln6.Temperature",
  "resolved_path": "Maceira.Cement.Kiln6.Temperature"
}
```

**Caching**: Metadata cached for 1 hour
**Auto-Resolution**: Short identifiers (for example `P431`) are automatically expanded via `search_tags` before querying Canary, ensuring the correct fully qualified path is returned.

**Example Usage:**
```
User: "What are the units for Kiln6.Temperature?"
Assistant uses: get_tag_metadata(tag_path="Kiln6.Temperature")
```

**Usage Guidance:** Obey the returned `confidence`/`next_step`. Let the workflow auto-select only when confidence ≥ 0.80; otherwise surface the `clarifying_question` and wait for the operator to add site/equipment/units.

---

### read_timeseries

Retrieve historical timeseries data for tags.

**Purpose**: Analyze plant performance and troubleshoot operational issues.

**Parameters:**
- `tag_names` (string or array, required): One or more tag identifiers (shorthand like `P431` is supported)
- `start_time` (string, required): Start time (ISO format or natural language)
- `end_time` (string, required): End time (ISO format or natural language)
- `bypass_cache` (boolean, optional): Skip cache (default: false)

**Supported Natural Language Times:**
- "yesterday"
- "last week"
- "past 24 hours"
- "last 30 days"
- "now"

**Returns:**
```json
{
  "success": true,
  "data": [
    {
      "timestamp": "2024-01-15T10:00:00Z",
      "value": 850.5,
      "quality": "Good",
      "tagName": "Maceira.400 - Clinker Production.431 - Kiln.Normalised.Energy.P431.Value",
      "requestedTag": "P431"
    },
    {
      "timestamp": "2024-01-15T10:01:00Z",
      "value": 851.2,
      "quality": "Good",
      "tagName": "Maceira.400 - Clinker Production.431 - Kiln.Normalised.Energy.P431.Value",
      "requestedTag": "P431"
    }
  ],
  "tag_names": ["P431"],
  "start_time": "2024-01-15T10:00:00Z",
  "end_time": "2024-01-15T10:10:00Z",
  "count": 10,
  "continuation": null,
  "resolved_tag_names": {"P431": "Maceira.400 - Clinker Production.431 - Kiln.Normalised.Energy.P431.Value"}
}
```

**Caching**: Recent queries (last 24h) cached for 5 minutes

**Example Usage:**
```
User: "Show me Kiln 6 temperature from yesterday"
Assistant uses: read_timeseries(
  tag_name="Kiln6.Temperature",
  start_time="yesterday",
  end_time="now"
)
```

**Usage Guidance:** Use this after resolving a tag path to verify units, engineering limits, and descriptions before running `read_timeseries`. It’s also helpful when responding to user questions such as “what is the unit for Kiln6.Temperature?”.

---

### get_tag_data2

High-capacity variant of `read_timeseries` that leverages Canary’s `getTagData2` endpoint.

**Purpose**: Pull larger windows (or aggregated traces) with fewer continuation hops by increasing `maxSize`.

**Parameters:**
- `tag_names` (string or array, required) – Same normalization rules as `read_timeseries`.
- `start_time`, `end_time` (string, required) – ISO or natural-language timestamps.
- `aggregate_name` (string, optional) – Canary aggregate (e.g., `TimeAverage2`).
- `aggregate_interval` (string, optional) – Interval string required when aggregates are requested.
- `max_size` (integer, optional) – Desired payload size before Canary paginates (default 1000).

**Returns:**
```json
{
  "success": true,
  "data": [
    {
      "timestamp": "2025-10-30T12:00:00Z",
      "value": 832.5,
      "quality": "Good",
      "tagName": "Secil.Portugal.Kiln6.Section15.ShellTemp"
    }
  ],
  "count": 720,
  "tag_names": [
    "Secil.Portugal.Kiln6.Section15.ShellTemp"
  ],
  "start_time": "2025-10-30T00:00:00Z",
  "end_time": "2025-10-31T00:00:00Z",
  "max_size": 5000,
  "aggregate_name": "TimeAverage2",
  "aggregate_interval": "00:05:00",
  "summary": {
    "site_hint": "Secil.Portugal",
    "total_samples": 720,
    "range": {
      "start": "2025-10-30T00:00:00Z",
      "end": "2025-10-31T00:00:00Z",
      "duration_seconds": 86400
    }
  }
}
```

**Usage Guidance:** Reach for `get_tag_data2` when you expect very large result sets or when you want Canary to compute aggregates server-side. Increase `max_size` first; if the response still indicates continuation, loop with the returned token just like `read_timeseries`.

#### getTagData vs getTagData2

| Capability | `read_timeseries` / `getTagData` | `get_tag_data2` / `getTagData2` |
| --- | --- | --- |
| Payload sizing | `page_size` (default 1000) | `max_size` (default 1000 but commonly raised to 5k+/call) |
| Continuation handling | Continuation token returned frequently on wide windows | Designed for higher ceilings; continuation appears less often |
| Aggregates | Optional but tuned for typical workloads | Same aggregate fields, but intended for processed data pipelines |
| Ideal use case | Standard reads, backwards-compatible flows | High-volume or aggregate-heavy reads needing fewer round trips |

---

### browse_status

Inspect view namespaces via the Canary `browseStatus` endpoint before issuing heavier metadata calls.

**Parameters:**
- `path` (string, optional) – Namespace prefix (for example `Secil.Portugal`). Defaults to the root namespace when omitted.
- `depth` (integer, optional) – Maximum tree depth (omit to use Canary’s default expansion).
- `include_tags` (boolean, optional) – When `false`, skip per-node tag lists to reduce payload size.
- `view` (string, optional) – Pass a Canary view name via the `views` query parameter for Tag-Security–protected namespaces.

**Returns:**
```json
{
  "success": true,
  "nodes": [
    {"path": "Secil.Portugal", "label": "Secil.Portugal", "status": "Good"}
  ],
  "tags": [],
  "next_path": "Secil.Portugal.Kiln6",
  "status": "Good",
  "hint": "Use browse_status to inspect namespaces before drilling into metadata."
}
```

**Usage Guidance:** Combine this tool with `get_asset_types` and `get_asset_instances` to validate that a view and its root nodes are reachable before issuing targeted reads.

**Script:** `python scripts/run_browse_status.py` lets ops step through branches interactively; see `docs/development/manual-tool-scripts.md` for CLI flags and environment knobs.

**Error Handling:**
- Missing `CANARY_VIEWS_BASE_URL` yields a helpful error message instead of stacking additional retries.
- Any HTTP failure returns `status` plus the raw Canary body so you can copy/paste into Jira/Slack when tracking issues.

---

### get_tag_properties

Retrieve detailed property dictionaries for one or more tags.

**Purpose**: Access engineering units, documentation, and historian metadata stored alongside each tag.

**Parameters:**
- `tag_paths` (array of strings, required): Fully qualified tag paths to fetch properties for.

**Returns:**
```json
{
  "success": true,
  "requested": [
    "P431"
  ],
  "properties": {
    "Secil.Portugal.Cement.Maceira.400 - Clinker Production.431 - Kiln.Normalised.Energy.P431.Value": {
      "Description": "Kiln 5 power consumption",
      "Units": "kW",
      "engLow": "0",
      "engHigh": "8000",
      "DataPermissions": "user_domainSecil(R);G_UNS_Admin(RW)"
    }
  },
  "count": 1,
  "cached": false,
  "resolved_paths": {
    "P431": "Secil.Portugal.Cement.Maceira.400 - Clinker Production.431 - Kiln.Normalised.Energy.P431.Value"
  }
}
```

**Example Usage:**
```
User: "Show me the engineering limits for kiln shell temperature"
Assistant uses: get_tag_properties(tag_paths=[
  "Secil.Portugal.Cement.Maceira.400 - Clinker Production.432 - Kiln.Normalised.Analog.Kiln_Shell_Temp_Average_Section_55.Value"
])
```

**Usage Guidance:** Use when you need the raw `properties` dictionary for several tags (UI pickers, audits). Results are keyed by resolved path so you can merge them with `get_tag_path` output.

**Error Handling:**
- Returns `success: false` when no tag paths are supplied.
- Authentication, HTTP, and network errors surface descriptive messages returned by the Canary API.

---

### list_namespaces

Discover available namespaces in the Canary historian.

**Purpose**: Understand the plant data structure and verify namespace configuration.

**Parameters:**
- `depth` (integer, optional): Hierarchy depth to return (default: 3)

**Returns:**
```json
{
  "success": true,
  "namespaces": [
    "Maceira",
    "Maceira.Cement",
    "Maceira.Cement.Kiln6"
  ],
  "nodes": [
    {
      "name": "Maceira",
      "path": "Maceira",
      "hasNodes": true,
      "hasTags": true
    },
    {
      "name": "Maceira.Cement",
      "path": "Maceira.Cement",
      "hasNodes": true,
      "hasTags": true
    },
    {
      "name": "Maceira.Cement.Kiln6",
      "path": "Maceira.Cement.Kiln6",
      "hasNodes": false,
      "hasTags": true
    }
  ],
  "count": 3
}
```

**Caching**: Namespaces cached for 1 hour

**Example Usage:**
```
User: "What sites are available?"
Assistant uses: list_namespaces()
```

**Usage Guidance:** Run this to verify the historian hierarchy or populate namespace pickers. If expected sites are missing, double-check the configured `CANARY_VIEWS_BASE_URL` and token permissions.

---

### get_server_info

Check Canary server health and MCP server capabilities.

**Purpose**: Verify connection and understand available features.

**Returns:**
```json
{
  "success": true,
  "server_info": {
    "canary_version": "23.1.0",
    "status": "online",
    "timezone": "UTC",
    "supported_aggregations": ["avg", "min", "max", "sum"]
  },
  "mcp_info": {
    "version": "1.0.0",
    "tools": ["search_tags", "get_tag_metadata", "read_timeseries"],
    "features": ["caching", "metrics", "circuit_breaker"]
  }
}
```

**Example Usage:**
```
User: "Is the Canary server online?"
Assistant uses: get_server_info()
```

**Usage Guidance:** Run after deployments or when diagnosing read/write failures to confirm Canary version, timezones, and aggregate support. Non-success responses usually indicate credential issues.

---

### write_test_dataset

Writes manual-entry samples to the Canary Store & Forward (SaF) API while enforcing the Epic 4 guardrails.

**Purpose**: Allow QA/test users to seed `Test/Maceira` or `Test/Outao` datasets without risking production historians.

**Parameters:**
- `dataset` (string, required) – Must be one of the whitelisted `Test/*` datasets (`CANARY_WRITE_ALLOWED_DATASETS`).
- `records` (array, required) – Each item must contain:
  - `tag` (string) – Fully qualified Test tag (e.g., `Test/Maceira/MCP.Audit.Success`).
  - `value` (number) – Numeric value written via `manualEntryStoreData`.
  - `timestamp` (string, optional) – ISO 8601 timestamp; defaults to now (UTC).
  - `quality` (string, optional) – Optional quality flag stored as the third TVQ element.
- `original_prompt` (string, required) – Natural-language instruction captured for auditing.
- `role` (string, required) – Must match `CANARY_TESTER_ROLES` (defaults to `tester`).
- `dry_run` (bool, optional) – Validate and preview without calling Canary (default `false`).

**Returns:**
```json
{
  "success": true,
  "write_success": true,
  "dataset": "Test/Maceira",
  "records_written": 1,
  "records": [
    {
      "tag": "Test/Maceira/MCP.Audit.Success",
      "timestamp": "2025-11-07T23:00:00.000Z",
      "value": 1,
      "quality": null
    }
  ],
  "original_prompt": "Log that the kiln temperature sanity check succeeded.",
  "role": "tester",
  "api_response": {"status": "OK"}
}
```

**Usage Guidance:**

1. Run with `dry_run=true` to ensure the dataset, role, and payload size pass validation.
2. Flip to `dry_run=false` once the summary looks correct. The tool captures the prompt/role for every call.
3. Clean up test data via Canary’s `/deleteRange` endpoint or the Historian UI when needed.
4. Writes are disabled entirely when `CANARY_WRITER_ENABLED=false`, and requests from non-tester roles return HTTP 403-style errors.

**Safety Notes:** The tool automatically rejects non-Test datasets, enforces the record-count limit (`CANARY_MAX_WRITE_RECORDS`, default 50), and requires an explicit tester role so production users can’t opt in accidentally.

---

## Performance & Monitoring Tools

### get_metrics

Get performance metrics in Prometheus format.

**Purpose**: Export metrics for monitoring systems (Prometheus, Grafana).

**Returns:**
```
# HELP canary_requests_total Total number of requests by tool
# TYPE canary_requests_total counter
canary_requests_total{tool_name="search_tags",status_code="200"} 42
canary_requests_total{tool_name="read_timeseries",status_code="200"} 156

# HELP canary_request_duration_seconds Request duration in seconds
# TYPE canary_request_duration_seconds histogram
canary_request_duration_seconds_bucket{tool_name="search_tags",le="0.5"} 35
canary_request_duration_seconds_bucket{tool_name="search_tags",le="1.0"} 40
...
```

**Usage Guidance:** Scrape this endpoint with Prometheus/Grafana. For CLI snapshots use `get_metrics_summary`, which returns aggregated JSON instead of exposition text.

---

### get_metrics_summary

Get human-readable performance metrics summary.

**Purpose**: Quick performance overview for operators.

**Returns:**
```json
{
  "success": true,
  "metrics": {
    "total_requests": 198,
    "by_tool": {
      "search_tags": {
        "request_count": 42,
        "latency": {
          "median": 1.2,
          "p95": 3.5,
          "p99": 5.1
        },
        "cache_hits": 10,
        "cache_misses": 32
      }
    },
    "cache_stats": {
      "total_hits": 45,
      "total_misses": 153
    },
    "active_connections": 3
  }
}
```

**Usage Guidance:** Ideal for CLI or script-based health checks (“how many requests have we served?”). For detailed scraping use `get_metrics`.

---

## Cache Management Tools

### get_cache_stats

Get cache performance statistics.

**Purpose**: Monitor cache effectiveness and optimize TTL settings.

**Returns:**
```json
{
  "success": true,
  "stats": {
    "entry_count": 42,
    "total_size_mb": 12.5,
    "max_size_mb": 100,
    "cache_hits": 150,
    "cache_misses": 30,
    "hit_rate_percent": 83.3,
    "evictions": 5,
    "total_accesses": 180
  }
}
```

**Use Case**: Determine if cache size or TTL needs adjustment

---

### invalidate_cache

Clear cached entries by pattern.

**Purpose**: Force fresh data retrieval when configuration changes.

**Parameters:**
- `pattern` (string, optional): SQL LIKE pattern (empty = invalidate all)

**Pattern Examples:**
- `""` - Invalidate all entries
- `"search:%"` - Invalidate all search results
- `"Kiln6%"` - Invalidate all Kiln 6 related data

**Returns:**
```json
{
  "success": true,
  "count": 15,
  "pattern": "search:%"
}
```

**Example Usage:**
```
User: "Clear the cache, I updated tag names"
Assistant uses: invalidate_cache(pattern="")
```

---

### cleanup_expired_cache

Remove expired entries to free storage.

**Purpose**: Manual cleanup of expired cache entries.

**Returns:**
```json
{
  "success": true,
  "count": 8
}
```

**Note**: Automatic cleanup happens during normal operations

---

## Utility Tools

### ping

Test MCP server connectivity.

**Purpose**: Verify server is running and responsive.

**Returns:**
```
"pong - Canary MCP Server is running!"
```

**Example Usage:**
```
User: "Is the MCP server working?"
Assistant uses: ping()
```

---

## Error Codes

All tools follow a consistent error response format:

```json
{
  "success": false,
  "error": "Error message describing what went wrong",
  "additional_context": "..."
}
```

**Common Error Types:**

1. **Authentication Errors**
   - Message: "Authentication failed: Invalid API token"
   - Fix: Check CANARY_API_TOKEN environment variable

2. **Connection Errors**
   - Message: "Cannot connect to Canary server"
   - Fix: Verify CANARY_SAF_BASE_URL and network connectivity

3. **Timeout Errors**
   - Message: "Request timed out after 30 seconds"
   - Fix: Increase CANARY_TIMEOUT or check server load

4. **Circuit Breaker Open**
   - Message: "Circuit breaker 'canary-api' is OPEN. Service unavailable, will retry in 45s"
   - Fix: Wait for circuit breaker to reset, check server health

5. **Validation Errors**
   - Message: "Search pattern cannot be empty"
   - Fix: Provide valid input parameters

---

## Best Practices

### Caching Strategy

1. **Use cache for repeated queries**: Don't bypass cache unless fresh data needed
2. **Monitor hit rate**: Aim for >70% hit rate with `get_cache_stats()`
3. **Invalidate after config changes**: Use `invalidate_cache()` after tag renames

### Performance Optimization

1. **Batch queries**: Request multiple tags together when possible
2. **Use natural language times**: "past 24 hours" is clearer than ISO timestamps
3. **Monitor latency**: Use `get_metrics_summary()` to track performance

### Error Handling

1. **Check success field**: Always verify `success: true` before using data
2. **Handle gracefully**: Display error messages to users for troubleshooting
3. **Retry on transient errors**: Connection errors may succeed on retry

### Query Patterns

**Good Pattern:**
```
1. search_tags("Kiln6*") → Get list of relevant tags
2. get_tag_metadata("Kiln6.Temperature") → Understand units/ranges
3. read_timeseries("Kiln6.Temperature", "past 24 hours", "now") → Get data
```

**Anti-Pattern:**
```
1. read_timeseries with wrong tag name → Error
2. Retry with different patterns → Multiple cache misses
```

### Rate Limiting

The server is configured for:
- **Concurrent connections**: 10 (configurable via CANARY_POOL_SIZE)
- **Request timeout**: 30s (configurable via CANARY_TIMEOUT)
- **Retry attempts**: 3-6 with exponential backoff

---

## Tool Usage Statistics

From production deployments:

| Tool | Avg Usage % | Typical Latency | Cache Hit Rate |
|------|-------------|-----------------|----------------|
| search_tags | 25% | 1.2s | 75% |
| read_timeseries | 45% | 2.5s | 60% |
| get_tag_metadata | 20% | 0.8s | 85% |
| list_namespaces | 5% | 1.5s | 90% |
| get_server_info | 5% | 0.5s | N/A |

---

## API Versioning

Current version: **v1.0.0**

Breaking changes will result in major version bump. Subscribe to release notes for updates.

---

## Support

For API questions or issues:
1. Check [Troubleshooting Guide](./troubleshooting/CANARY_API_DIAGNOSIS.md)
2. Review [Example Queries](./examples.md)
3. Enable DEBUG logging: `LOG_LEVEL=DEBUG`
4. Review logs for detailed error information

---

*Last Updated: Story 2.6 Implementation*
*API Version: 1.0.0*

### get_aggregates

Retrieve the list of aggregate functions supported by the Canary Views API.

**Purpose**: Programmatically discover which aggregate names (`TimeAverage2`, `Interpolated`, etc.) are valid before issuing data reads.

**Parameters**: none

**Returns:**
```json
{
  "success": true,
  "aggregates": [
    "TimeAverage2",
    "Interpolated"
  ],
  "count": 12
}
```

**Usage Guidance:** Call this tool once per session (results rarely change) and cache the names in your LLM prompt so you can recommend valid aggregates to operators.

---

### get_asset_types

Enumerate Canary asset types stored in a particular view.

**Parameters:**
- `view` (string, optional) – Canary asset view (defaults to `CANARY_ASSET_VIEW` when omitted).

**Returns:**
```json
{
  "success": true,
  "view": "Views/Maceira.Assets",
  "asset_types": [
    {"name": "Kiln", "description": "Rotary kiln model"},
    {"name": "Preheater", "description": "Cyclone string"}
  ],
  "count": 2
}
```

**Usage Guidance:** Use this before prompting an LLM to reason over Canary Asset Models. Pair it with `get_asset_instances` to drill into specific equipment and then feed the resulting instance paths to other MCP tools.

---

### get_asset_instances

List instances for a given asset type (optionally filtered by path).

**Parameters:**
- `asset_type` (string, required) – Asset type identifier returned by `get_asset_types`.
- `view` (string, optional) – Overrides `CANARY_ASSET_VIEW`.
- `path` (string, optional) – Limits the search to a subtree.

**Returns:**
```json
{
  "success": true,
  "asset_type": "Kiln",
  "instances": [
    {"path": "Kilns/Line1/K6", "displayName": "Kiln 6"},
    {"path": "Kilns/Line2/K7", "displayName": "Kiln 7"}
  ],
  "count": 2
}
```

**Usage Guidance:** After locating an asset instance, feed its `path` and tags into `get_tag_path` or `read_timeseries` to gather the actual historian values tied to that asset.

---

### get_events_limit10

Fetch recent Canary event records (default limit = 10).

**Parameters:**
- `limit` (integer, optional) – Number of events to retrieve (default 10).
- `view`, `start_time`, `end_time` (strings, optional) – Narrow the query.

**Returns:**
```json
{
  "success": true,
  "events": [
    {"timestamp": "2025-11-07T23:00:00Z", "message": "Kiln6 temp high", "severity": "Warning"}
  ],
  "count": 1
}
```

**Usage Guidance:** Use this tool when an operator asks “What alarms fired recently?” or when you need qualitative context (warnings, trips) to pair with numeric timeseries data.

---
