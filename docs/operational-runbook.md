# Operational Runbook for Universal Canary MCP Server

This document provides essential procedures for operating and maintaining the Universal Canary MCP Server, covering routine tasks, security practices, and incident response.

---

## 1. Reindexing the Vector Index (if enabled)

The vector index is used for semantic search capabilities (e.g., `get_tag_path` tool) and needs to be rebuilt when the underlying tag catalog changes.

**Procedure:**

1.  **Verify Source Data:** Ensure the source tag catalog file (e.g., `docs/aux_files/Canary Resources/Canary_Path_description_maceira.json`) is up-to-date.
2.  **Execute Reindexing Script:**
    ```bash
    uv run python scripts/build_vector_index.py \
      --source "docs/aux_files/Canary Resources/Canary_Path_description_maceira.json" \
      --out data/vector-index
    ```
    *   Replace the `--source` path if your catalog is located elsewhere.
    *   The `--out` directory (`data/vector-index`) is the default location where the index files (`catalog.jsonl`, `embeddings.npy`, `records.json`, `meta.json`) will be generated.
3.  **Verify Index:** Check the script output for any errors. A successful run will indicate the creation of the index files.
4.  **Restart MCP Server:** For the new index to be loaded, the MCP server must be restarted.

---

## 2. Key Rotation (Canary API Token)

Regular rotation of API tokens is a security best practice.

**Procedure:**

1.  **Generate New Token in Canary Identity:**
    *   Log in to the Canary Identity service.
    *   Navigate to the API Tokens section.
    *   Generate a new API token for the MCP server's dedicated Canary user. Ensure it has the necessary read/write permissions (as per the "Write API Authentication" documentation).
2.  **Update Environment Configuration:**
    *   Locate the `.env` file used by your MCP server deployment (or the environment variables configured in your Docker/orchestration setup).
    *   Update the `CANARY_API_TOKEN` variable with the newly generated token.
    ```ini
    CANARY_API_TOKEN=your_new_api_token_here
    ```
3.  **Restart MCP Server:** Restart the MCP server to pick up the new `CANARY_API_TOKEN`.
4.  **Verify Connection:** After restarting, use the `ping` tool or `get_server_info` tool via your MCP client (e.g., Claude Desktop) to confirm successful connection with the new token.
5.  **Revoke Old Token (Optional but Recommended):** Once the new token is confirmed to be working, revoke the old token in the Canary Identity service to minimize security exposure.

---

## 3. Incident Handling and Recovery Procedures

This section outlines general steps for responding to and recovering from incidents affecting the MCP server.

### 3.1. Initial Triage

1.  **Check MCP Client Status:** Is the MCP client (e.g., Claude Desktop) reporting a connection error?
2.  **Review MCP Server Logs:** Access the MCP server logs (configured via `LOG_LEVEL` in `.env`). Look for `ERROR` or `CRITICAL` messages.
    *   Common log locations: `logs/mcp-server-canary-historian.log` (if configured), or console output if running interactively.
3.  **Check Server Health Endpoint:** If the server is running in HTTP mode, access the `/health` endpoint (e.g., `http://localhost:6000/health`) to check its status, circuit breaker state, and cache health.
4.  **Verify Canary API Connectivity:**
    *   Use the `get_server_info` tool via the MCP client.
    *   If the MCP server is unresponsive, try to `curl` the Canary API directly from the server's host to rule out network issues.

### 3.2. Common Incidents & Solutions

#### A. MCP Server Unresponsive / Not Starting

*   **Symptom:** `ping` tool fails, server logs show startup errors.
*   **Possible Causes:**
    *   Incorrect environment variables (`.env` file).
    *   Missing dependencies (`uv sync` not run or failed).
    *   Port conflict (if running in HTTP mode).
*   **Solution:**
    1.  Review `uv run python -m canary_mcp.server` output for errors.
    2.  Validate `.env` configuration, especially `CANARY_API_TOKEN`, `CANARY_VIEWS_BASE_URL`, `CANARY_SAF_BASE_URL`.
    3.  Ensure all Python dependencies are installed (`uv sync --locked --dev`).
    4.  If port conflict, change `MCP_SERVER_PORT` in `.env` (for HTTP mode).

#### B. Canary API Connection Errors

*   **Symptom:** MCP tools fail with "Authentication failed", "Cannot connect to Canary server", or "Request timed out".
*   **Possible Causes:**
    *   Expired or invalid `CANARY_API_TOKEN`.
    *   Canary Historian server is down or unreachable.
    *   Network issues between MCP server and Canary API.
    *   Incorrect `CANARY_VIEWS_BASE_URL` or `CANARY_SAF_BASE_URL`.
*   **Solution:**
    1.  **Check `CANARY_API_TOKEN`:** Perform Key Rotation procedure (Section 2).
    2.  **Verify Canary Server Status:** Contact Canary Historian administrators.
    3.  **Network Check:** From the MCP server host, `ping` or `curl` the Canary API base URLs to confirm network connectivity.
    4.  **Configuration:** Double-check `CANARY_VIEWS_BASE_URL` and `CANARY_SAF_BASE_URL` in `.env`.

#### C. Circuit Breaker Open

*   **Symptom:** `/health` endpoint shows `circuit_breakers` state as "open", MCP tools return "Circuit breaker 'canary-api' is OPEN" errors.
*   **Possible Causes:** Sustained failures when calling the Canary API, leading the circuit breaker to trip to protect the Canary system.
*   **Solution:**
    1.  **Investigate Root Cause:** Determine why the Canary API calls were failing (e.g., Canary server down, network issues, invalid token). Refer to "Canary API Connection Errors" above.
    2.  **Wait for Reset:** The circuit breaker will automatically attempt to close after its `timeout_duration` (e.g., 60 seconds).
    3.  **Manual Intervention (if necessary):** If the underlying issue is resolved but the circuit breaker remains open, a restart of the MCP server will reset its state.

#### D. Performance Degradation / Slow Responses

*   **Symptom:** MCP tools are slow, `get_metrics_summary` shows high latencies.
*   **Possible Causes:**
    *   High load on MCP server or Canary API.
    *   Inefficient queries (e.g., very wide time ranges, too many tags).
    *   Cache not effective (low hit rate).
*   **Solution:**
    1.  **Review Queries:** Optimize LLM prompts to generate more focused queries (narrow time ranges, fewer tags).
    2.  **Check Cache:** Use `get_cache_stats` to monitor cache hit rate. If low, consider adjusting cache TTLs or increasing cache size.
    3.  **Scale Resources:** If running in a containerized environment, increase CPU/memory allocated to the MCP server.
    4.  **Canary API Performance:** Investigate Canary Historian performance if `get_metrics_summary` indicates high Canary API latencies.

---

## 4. Monitoring and Alerting

*   **Metrics:** Scrape the `/metrics` endpoint (Prometheus format) with your monitoring system (e.g., Prometheus + Grafana) to track key performance indicators (request rates, latencies, error rates, cache stats, circuit breaker state).
*   **Logs:** Centralize MCP server logs into a log management system for easier searching and alerting on `ERROR` or `CRITICAL` events.
*   **Health Checks:** Configure your orchestration platform (e.g., Kubernetes, Docker Compose health checks) to regularly poll the `/health` endpoint.

---

_Last Updated: 2025-11-08
