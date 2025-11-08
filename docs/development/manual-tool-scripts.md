# Manual MCP Tool Scripts

This catalog lists every manual entry point we ship for exercising MCP tools without hitting the full MCP client stack. Each script is self-contained and outputs JSON so operators can copy/paste troubleshooting logs into incident tickets.

| Script | MCP Tool (depends on env) | Purpose | Notes |
| --- | --- | --- | --- |
| `scripts/run_get_metrics.py` | `get_metrics` | Emit raw Prometheus exposition to verify the MCP server is collecting request/latency metrics. | No Canary credentials required; ideal for quick health checks. |
| `scripts/run_get_cache_stats.py` | `get_cache_stats` | Show cache hit/miss counts, entry totals, and TTLs. | Useful after deployments to confirm metadata caches warm correctly. |
| `scripts/run_cleanup_expired_cache.py` | `cleanup_expired_cache` | Trigger cache eviction and see how many entries were removed. | Run before reloading new catalogs to ensure stale payloads drop. |
| `scripts/run_get_health.py` | `get_health` | Prints consolidated health (circuit breaker, cache, metrics). | Requires configured `CANARY_VIEWS_BASE_URL` for the metrics probe. |
| `scripts/run_get_events_limit10.py` | `get_events_limit10` | Fetch recent historian events for a given view or global scope. | Accepts `--view`, `--limit`, and time window overrides; needs `CANARY_VIEWS_BASE_URL` and API token via `CanaryAuthClient`. |
| `scripts/run_get_tag_data2.py` | `get_tag_data2` | Read timeseries samples or aggregates for one or more tags to validate data access. | Defaults to a 30‑minute window for `Maceira.Cement.Kiln6.Temperature.Outlet`. Supply `--tags`, `--aggregate-name`, etc. |
| `scripts/run_invalidate_cache.py` | `invalidate_cache` | Purge cache entries matching an optional pattern. | Handy before injecting new catalog resources or after configuration changes. |
| `scripts/run_write_test_dataset.py` | `write_test_dataset` | Dry-run (or execute) writes into `Test/*` datasets for manual telemetry. | Defaults to `dry_run`; pass `--execute` to actually hit Canary SAF (requires `CANARY_SAF_BASE_URL`, `CANARY_API_TOKEN`, and tester role membership). |
| `scripts/run_browse_status.py` | `browse_status` | Walk view/namespace hierarchies and verify the `nextPath`/`tags` payloads. | Use `--path`, `--depth`, `--no-tags`, and `--view` to throttle results; requires `CANARY_VIEWS_BASE_URL`. |

**Quick Reference**

- All scripts append `src/` to `sys.path` so they can be invoked from anywhere (no uv wrapper needed).  
- Most tools require a valid Canary session token; configure `.env` with `CANARY_API_TOKEN`, `CANARY_VIEWS_BASE_URL`, and (for write) `CANARY_SAF_BASE_URL`.  
- The `run_write_test_dataset.py` script defaults to a dry run—flip `--execute` only when you really want data written.  
- Use `scripts/test_mcp_tools.py` for a consolidated smoke test that hits many of these tools programmatically.  
- Record the printed JSON (request_id, error, payload) when escalating incidents—this makes root cause analysis faster than “the tool failed.”
