# Secil Canary Historian MCP Server

Model Context Protocol (MCP) server providing seamless access to Canary Historian plant data for LLM-powered applications.

## Overview

The Universal Canary MCP Server enables LLM clients (Claude Desktop, Continue, etc.) to interact with Canary Historian industrial data through natural language queries. This server implements the MCP protocol standard, exposing tools that allow engineers and analysts to access real-time and historical plant data without manual API integration.

**Project Status:** MVP implemented | Secil Cement Maceira site supported | Mortars Supported | Outão site ongoing

Quick links:
- API Contracts (local docs and security notes): see "API Contracts (Local Docs)" below.

## Features

- ✅ **MCP Protocol Implementation** - FastMCP-based server with tool registration
- ✅ **Ping Tool** - Connection testing and health check
- ✅ **Environment Configuration** - Flexible configuration via environment variables
- ✅ **Local Tag Dictionary** - Offline index seeded from Canary exports keeps natural-language tag mapping reliable even when API search misses
- ✅ **Auto Tag Resolution** - Short identifiers (for example `P431`) transparently resolve to fully-qualified Canary paths across all tools
- ✅ **Comprehensive Testing** — Unit/integration suites plus automated health checks
- ✅ **Canary API Integration** - Coming in Story 1.2
- ✅ **Data Access Tools** - Coming in Stories 1.3-1.7

## Installation

Two transport modes are supported and both work without administrator rights:

| Mode | Transport | When to use | Install entry point |
| --- | --- | --- | --- |
| **Local STDIO (default)** | STDIO piping between the MCP client and this repo | Individual laptops, air‑gapped testing, fastest iteration | Run `scripts/Install-Canary-MCP.cmd` (wraps `deploy_canary_mcp.ps1`) or follow the [non-admin Windows guide](docs/installation/non-admin-windows.md). No elevation required. |
| **Remote HTTP/SSE** | HTTP server with SSE streaming | Team-shared VM or container deployment | Use the same repo on a server/VM and expose port 6000 (see [Remote HTTP deployment](docs/installation/REMOTE_HTTP_DEPLOYMENT.md)). |

**STDIO validation checklist**
1. Double-click `Install-Canary-MCP.cmd` (or run `deploy_canary_mcp.ps1`) and provide the Canary URLs when prompted.
2. After the script finishes, reopen Claude Desktop (or your MCP client) and run the `ping` tool. Success message: “pong – Canary MCP Server is running!”
3. If `ping` fails, rerun the installer with `--verbose` or consult `docs/troubleshooting/DEBUG_MCP_SERVER.md`.

For hands-on configuration via uv, jump down to [Quick setup (uv)](#quick-setup-uv).

## MCP Server Capabilities

The Canary MCP Server exposes a rich set of capabilities for interacting with the Canary Historian. These are categorized into Tools, Prompts (Workflows), and Resources.

### Access Control

Access to the MCP server is secured using OAuth 2.0, the industry-standard protocol for authorization. MCP clients must present a valid bearer token to access the server's resources.

#### Canary API Authentication

Authentication to the underlying Canary API is handled transparently by the server. The `CANARY_API_TOKEN` environment variable must be set with a valid API token, which the server uses for all communication with the Canary Historian.

### Tools

Tools are functions that can be directly executed by an MCP client.

*   **`ping()`** – sanity check that MCP is reachable. Use before a session starts; it never touches Canary.
*   **`get_asset_catalog()`** – quick, offline peek at the curated tag catalog. Ideal for metadata-only discovery or when Canary is offline. Responses obey the 1 MB guardrail and truncate with guidance when necessary.
*   **`search_tags(search_pattern)`** – live Canary browse when you already know part of the tag name. Avoid wildcards; pair with `get_tag_path` for NL flows.
*   **`get_tag_metadata(tag_path)`** – fetch detailed properties (units, eng limits, descriptions) once you know the fully qualified path. Pitfall: requires the exact historian path; use `get_tag_path` to resolve aliases first.
*   **`get_tag_path(description)`** – NL → historian path workflow. Returns `confidence`, `confidence_label`, and `clarifying_question` so LLMs know when to proceed or ask the user for more context.
*   **`get_tag_properties(tag_paths)`** – batched property lookup for multiple paths. Handy when cross-checking units before issuing large read queries.
*   **`list_namespaces()`** – discover namespace roots/folders. Use this to confirm a plant’s structure or to seed UI pickers.
*   **`get_last_known_values(tag_names)`** – grab the most recent sample for one or more tags. Automatically falls back to configured views if no data exists in the requested window.
*   **`read_timeseries(tag_names, start_time, end_time)`** – canonical path for historical data. Accepts ISO timestamps or Canary relative expressions; watch the `continuation` token for paging.
*   **`get_tag_data2(tag_names, start_time, end_time, aggregate_name?, aggregate_interval?, max_size?)`** – high-capacity sibling to `read_timeseries` that hits Canary’s `getTagData2` endpoint. Use it for large windows or server-side aggregates when you want fewer continuation hops (tune `max_size`).
*   **`get_aggregates()`, `get_asset_types(view?)`, `get_asset_instances(asset_type, view?, path?)`, `get_events_limit10(limit?, …)`** – metadata helpers for Canary Views assets/events. They power richer LLM prompts without hitting production historians.
*   **`write_test_dataset(dataset, records, original_prompt, role, dry_run=False)`** – gated write pathway to the Canary SAF API. Only `Test/Maceira` and `Test/Outao` datasets are allowed, and callers must pass a tester role (defaults to `tester`). Use `dry_run=True` to validate payloads before sending and keep `records` under the `CANARY_MAX_WRITE_RECORDS` limit.
*   **`get_server_info()`** – reports Canary capabilities (timezones, aggregates) and MCP settings. Run it after deployments to ensure the environment is wired correctly.
*   **`get_metrics()` / `get_metrics_summary()`** – Prometheus output vs. human-readable summary of request counts, latency, cache stats. Use for health dashboards or quick CLI checks.
*   **`get_cache_stats()`**, **`invalidate_cache(pattern)`**, **`cleanup_expired_cache()`** – manage the local metadata cache when debugging stale data.
*   **`get_health()`** – consolidated MCP/circuit-breaker status plus cache/metrics snapshots. Wire it into ops monitors for a high-level heartbeat.

### Prompts (Workflows)

Prompts are structured, multi-step workflows that guide an LLM or MCP client through a complex process.

*   **`tag_lookup_workflow`**: A guided workflow for translating a natural-language request (e.g., "the main kiln temperature") into a precise Canary tag path. It orchestrates the use of `get_asset_catalog`, `search_tags`, and `get_tag_properties`, and emits confidence/clarifying-question signals so LLMs know when to double-check with the user.
*   **`timeseries_query_workflow`**: A deterministic workflow for safely and efficiently retrieving historical data. It walks through tag resolution, natural-language time parsing, payload assembly, and continuation handling before summarising results back to the user.

See [`docs/workflows/prompt-workflows.md`](docs/workflows/prompt-workflows.md) for the full step-by-step playbooks, including inputs, outputs, and example conversations.

### Resources

Resources provide static data or documentation to the MCP client to aid in constructing valid queries.

*   **`maceira_tag_catalog`**: A JSON resource containing the curated list of tags for the Maceira site, including natural-language descriptions and engineering units. This is the primary reference for tag discovery.
*   **`canary_time_standards`**: A JSON resource that provides a reference guide for Canary's relative time expressions (e.g., "Now-1d") and the server's default timezone (`Europe/Lisbon`).
*   **Reference docs**: See [`docs/resources/resource-index.md`](docs/resources/resource-index.md) for every on-disk artifact (tag catalog, time standards, Postman exports) plus RAG feasibility notes and size-guardrail reminders.

### Metadata-only Tag Discovery

You can resolve tags without touching the live Canary API by combining the local resources:
1. Call `get_asset_catalog` / read `resource://canary/tag-catalog` to fetch candidate paths, descriptions, and units.
2. Use `get_local_tag_candidates` (from `src/canary_mcp/tag_index.py`) to score the catalog entries against your keywords.
3. Feed the results into `get_tag_path`, which now emits `confidence`, `confidence_label`, and `clarifying_question` fields so LLMs know whether to proceed (`confidence ≥ 0.80`) or ask for more context.
4. Keep responses under the 1 MB guardrail (`CANARY_MAX_RESPONSE_BYTES`, default 1 000 000). If a response is truncated, the payload includes a preview plus guidance to narrow the query.

### Expected Workflow for an MCP Client / LLM

To effectively interact with the Canary Historian, MCP clients and LLMs should follow a structured workflow that leverages the server's capabilities. The server provides guided **Prompts (Workflows)** and static **Resources** to ensure reliable and efficient data access.

1.  **Tag Discovery**: To find a specific tag, the client should use the **`tag_lookup_workflow`**. This prompt orchestrates the use of tools like `get_asset_catalog` and `search_tags` along with the `maceira_tag_catalog` resource to translate a user's request (e.g., "main kiln temperature") into a fully qualified Canary tag path.

2.  **Data Retrieval**: Once a tag path is identified, the client should use the **`timeseries_query_workflow`**. This prompt ensures that time ranges are correctly specified (referencing `canary_time_standards`) and that the `read_timeseries` tool is called with valid parameters to fetch the historical data.

By following these workflows, the client can reliably navigate the Canary Historian, resolve ambiguity, and retrieve data efficiently, abstracting away the complexity of the underlying API.

## Quick setup (uv)

Fast path to run locally with uv on Windows, macOS, or Linux.

Prerequisites:
- Python 3.12 or 3.13 available on PATH (portable Python works on Windows)
- uv installed

Steps:
```bash
# 1) Install uv (one-time)
# Windows PowerShell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
# macOS/Linux
curl -fsSL https://astral.sh/uv/install.sh | sh

# 2) Clone and enter repo
git clone <repository-url>
cd BD-Canary-MCP

# 3) Create and activate virtual env + install deps
uv sync --locked --dev

# 4) Configure environment from template
copy .env.example .env  # Windows
# or
cp .env.example .env    # macOS/Linux
# Then edit .env with your Canary credentials (no secrets committed)

uv run pip install .

# 5) Validate installation
uv run python scripts/validate_installation.py

# 6) Start the MCP server
uv run canary-mcp
# or
uv run python -m canary_mcp.server
```

Notes:
- Configuration is loaded from .env using python-dotenv.
- Use uv run pytest to execute tests; uvx ruff/black for lint/format.
- For Claude Desktop integration, see the section below.

## Architecture

```
BD-hackaton-2025-10/
├── src/
│   └── canary_mcp/          # Main MCP server package
│       ├── __init__.py      # Package initialization
│       └── server.py        # MCP server with tool definitions
├── tests/
│   ├── unit/                # Unit tests
│   │   └── test_project_structure.py
│   └── integration/         # Integration tests
│       └── test_mcp_server_startup.py
├── config/                  # Configuration files
├── docs/                    # Project documentation
├── pyproject.toml          # Python project metadata & dependencies
├── .env.example            # Environment variable template
└── README.md               # This file
```

### Component Architecture

```
┌─────────────────────────────────────────┐
│   LLM Client (Claude Desktop, etc.)    │
└────────────────┬────────────────────────┘
                 │ MCP Protocol
                 ↓
┌─────────────────────────────────────────┐
│      Universal Canary MCP Server        │
│  ┌───────────────────────────────────┐  │
│  │  FastMCP Server                   │  │
│  │  - Tool Registration              │  │
│  │  - Request Handling               │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │  MCP Tools                        │  │
│  │  - ping (connection test)         │  │
│  │  - [Canary data tools]    │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
                 ↓ (Future)
┌─────────────────────────────────────────┐
│      Canary Views Web API               │
│  - Authentication                       │
│  - Historical Data Access               │
│  - Real-time Data Streaming             │
└─────────────────────────────────────────┘
```

## Deployment

Three deployment modes are now supported. Choose the one that fits your workflow and follow the linked guides for the full playbook.

| Option | Transport | Best for | Documentation |
| --- | --- | --- | --- |
| Local MCP (STDIO) | STDIO | Developer laptops, single-machine analysis | [Deployment summary](docs/installation/DEPLOYMENT_PACKAGE_SUMMARY.md#11-local-mcp-server-stdio) |
| Remote MCP (HTTP SSE) | HTTP + SSE | Shared VM (e.g. `vmhost8.secil.pt`), department rollouts | [Remote HTTP deployment](docs/installation/REMOTE_HTTP_DEPLOYMENT.md) |
| Containerised MCP | HTTP + SSE | Docker/Podman, CI/CD, Kubernetes | [Container guide](docs/installation/docker-installation.md) |

### Local STDIO Quick Start
```bash
uv sync --locked --dev
cp .env.example .env  # set CANARY_MCP_TRANSPORT=stdio and credentials
uv run python -m canary_mcp.server
```

### Remote HTTP SSE Quick Start
```bash
# edit .env on the server
CANARY_MCP_TRANSPORT=http
CANARY_MCP_HOST=0.0.0.0
CANARY_MCP_PORT=6000

# then launch
uv run python -m canary_mcp.server
```

Verify the listener with:
```bash
scripts/check_mcp.sh http http://vmhost8.secil.pt:6000
```

### Container Quick Start
```bash
docker compose up --build
# or
podman-compose up --build
```

Inject `.env` via environment variables or bind mount and place the container behind corporate ingress as needed.

### Example `.env` entries (copy from `.env.example`)

```ini
# Transport (stdio keeps everything local)
CANARY_MCP_TRANSPORT=stdio
# Canary endpoints (read & write)
CANARY_SAF_BASE_URL=https://scunscanary.secil.pt/api/v1
CANARY_VIEWS_BASE_URL=https://scunscanary.secil.pt
# Optional: default view scoping for read_timeseries
CANARY_DEFAULT_VIEW=Secil.Portugal.Default
# Asset metadata view for get_asset_types / get_asset_instances
CANARY_ASSET_VIEW=Views/Maceira.Assets
# Token issued in Canary Identity (Tag Security applies)
CANARY_API_TOKEN=00000000-0000-0000-0000-000000000000
# Write tool guardrails
CANARY_WRITER_ENABLED=true
CANARY_TESTER_ROLES=tester,qa
CANARY_WRITE_ALLOWED_DATASETS=Test/Maceira,Test/Outao
# Vector/RAG knobs (optional)
CANARY_ENABLE_VECTOR_SEARCH=false
CANARY_VECTOR_INDEX_PATH=data/vector-index
CANARY_VECTOR_TOP_K=5
CANARY_VECTOR_DIM=512
CANARY_VECTOR_HASH_SEED=0
```

Set `CANARY_MCP_TRANSPORT=http` plus `CANARY_MCP_HOST`/`CANARY_MCP_PORT` when you promote the same build to a remote VM.

Need a token or Tag Security refresher? See [API Contracts (Local Docs)](#api-contracts-local-docs) for links to the Canary READ/WRITE PDFs inside `docs/aux_files/Canary API`.

## API Contracts (Local Docs)

- Location: `docs/aux_files/Canary API`
  - Read (Views) API: “Canary Labs Historian Views Service API Documentation (v25.4)”
  - Write (Store & Forward) API: “Canary Labs Historian Store and Forward Service API Documentation (v25.3)”
- Authentication & Tag Security
  - Use `apiToken` (configured in Canary Identity) for all API calls. Each token maps to a Canary user.
  - If Tag Security is enabled, the Canary user must have read permissions for Views (READ) and write permissions for the target DataSet(s) (WRITE).
  - For WRITE via SaF, if the service is remote from the Historian, configure the SaF service with an API token as well.
  - Backwards compatibility: some endpoints accept `accessToken` if `apiToken` is not provided; `/getUserToken` remains for legacy flows when credentials are linked to an Identity user.
- Project policy: WRITE tool is gated to `Test/*` datasets only (e.g., `Test/Maceira`, `Test/Outao`). The helper `canary_mcp.write_guard.validate_test_dataset` enforces this rule before any payload is sent to Canary.

### Example Requests (READ/WRITE)

- READ (Views) — getTagData
  - Endpoint: `POST {VIEWS_BASE}/api/v2/getTagData`
  - Body (example):
    ```json
    {
      "apiToken": "<token>",
      "tags": ["Maceira.Cement.Kiln6.Temperature.Outlet"],
      "startTime": "2025-10-30T00:00:00Z",
      "endTime": "2025-10-31T00:00:00Z",
      "pageSize": 1000
    }
    ```
  - Response (shape excerpt):
    ```json
    {
      "data": [
        {"timestamp": "2025-10-30T12:00:00Z", "value": 26.2, "quality": "Good", "tagName": "...Outlet"}
      ]
    }
    ```

- WRITE (Store & Forward) — session and write sample
  - Session (token creation flow depends on deployment; refer to SaF docs)
    - Optionally set `autoCreateDatasets": true` for test environments.
  - Write request (conceptual example, see SaF v25.3 for exact schema):
    ```json
    {
      "apiToken": "<token>",
      "dataSet": "Test/Maceira",
      "points": [
        {"path": "Test/Maceira/MCP.Telemetry.Success", "timestamp": "2025-10-31T12:00:00Z", "value": 1}
      ]
    }
    ```

## Usage

### Test with MCP Inspector

Use the MCP Inspector to interactively test the server without a client:

```bash
npx @modelcontextprotocol/inspector uv --directory . run canary-mcp
```

This launches the Inspector UI in your browser and starts the server via uv from the current directory.

### Running the MCP Server

```bash
# Start the server
uv run canary-mcp

# Or run directly
uv run python -m canary_mcp.server
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run unit tests only
uv run pytest -m unit -q

# Run integration tests only (using pytest)
uv run pytest -m integration -q

# Run integration tests with a specific environment (as used in CI)
python scripts/run_integration_tests.py --env test
```

### CLI Tool Validator

Use the bundled script to exercise the main MCP tools (skipping network-dependent calls when credentials are absent):

```bash
python scripts/test_mcp_tools.py \
  --sample-tag "Maceira.Cement.Kiln6.Temperature.Outlet" \
  --search-pattern "Kiln*Temp"
```

### Operational Smoke Scripts

Quick one-off tests for ops/SRE use cases:

| Script | Purpose |
| --- | --- |
| `python scripts/run_get_metrics.py` | Dumps the Prometheus exposition string. |
| `python scripts/run_get_cache_stats.py` | Shows cache hit/miss counts and entry totals. |
| `python scripts/run_cleanup_expired_cache.py` | Forces a cache cleanup cycle and prints the summary. |
| `python scripts/run_get_health.py` | Emits the consolidated MCP health payload (circuit breaker, cache, metrics). |

### Writing Test Telemetry (Test/Maceira + Test/Outao)

1. **Build the payload** – each record needs a fully qualified tag under the allowed Test dataset, a numeric value, and (optionally) an ISO timestamp. Missing timestamps default to "now" (UTC).
2. **Dry-run first** – set `dry_run=true` to validate dataset, role, and payload size before anything touches Canary.
3. **Tester-only** – the `role` argument must match `CANARY_TESTER_ROLES` (defaults to `tester`). Non-matching roles receive a 403 response.
4. **Cleanup guidance** – use Canary’s `/deleteRange` endpoint or the historian UI to remove test data after experiments. Because writes are confined to `Test/*`, production datasets remain untouched.

Sample MCP payload:

```jsonc
{
  "tool": "write_test_dataset",
  "args": {
    "dataset": "Test/Maceira",
    "records": [
      {
        "tag": "Test/Maceira/MCP.Audit.Success",
        "value": 1,
        "timestamp": "2025-11-07T23:00:00Z"
      }
    ],
    "original_prompt": "Log that the kiln temperature sanity check succeeded.",
    "role": "tester",
    "dry_run": true
  }
}
```

Flip `dry_run` to `false` once the preview looks correct. The response echoes the captured prompt, role, and record details for auditing.

### Vector Index / RAG Pipeline (Optional)

1. **Build the JSONL + embeddings**
   ```bash
   python scripts/build_vector_index.py \
     --source "docs/aux_files/Canary Resources/Canary_Path_description_maceira.json" \
     --out data/vector-index
   ```
   - Produces `catalog.jsonl`, `embeddings.npy`, `records.json`, and `meta.json`.
   - Uses a deterministic hash-based embedding (configurable via `CANARY_VECTOR_DIM` / `--dimension`) so the index can be rebuilt without external services or GPU dependencies.
2. **Enable semantic search**
   ```
   CANARY_ENABLE_VECTOR_SEARCH=true
   CANARY_VECTOR_INDEX_PATH=data/vector-index
   CANARY_VECTOR_TOP_K=5
   ```
   Keep these in `.env`. When enabled, `get_local_tag_candidates` augments keyword hits with top semantic matches (still capped by the 1 MB payload guard).
3. **Rebuild cadence**
   - Re-run the script whenever the catalog JSON changes.
   - The resulting `data/vector-index/` directory is ignored by Git; archive it separately if you need to share the index.

> Semantic suggestions are additive—the inverted index remains the source of truth, and vector matches include `"source": "vector-index"` metadata so MCP clients can explain where each candidate originated.

The script prints a human-readable PASS/WARN/FAIL summary and respects the global 1 MB response guardrail.

### Testing the Ping Tool

```python
# Python interactive test
from canary_mcp.server import ping

# Call the ping tool function
response = ping.fn()
print(response)
# Output: "pong - Canary MCP Server is running!"
```

### Connecting to Claude Desktop

The primary way to use this MCP server is through Claude Desktop. Follow these steps to connect:

#### 1. Locate Claude Desktop Configuration File

The configuration file is located at:
```
%APPDATA%\Claude\claude_desktop_config.json
```

Full path (Windows):
```
C:\Users\<YourUsername>\AppData\Roaming\Claude\claude_desktop_config.json
```

#### 2. Add MCP Server Configuration

Create or edit the config file with the following content:

```json
{
  "mcpServers": {
    "canary-mcp-server": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\Github\\BD\\BD-hackaton-2025-10",
        "run",
        "python",
        "-m",
        "canary_mcp.server"
      ],
      "env": {
        "PYTHONPATH": "C:\\Github\\BD\\BD-hackaton-2025-10\\src"
      }
    }
  }
}
```

**Important Notes:**
- Replace `C:\\Github\\BD\\BD-hackaton-2025-10` with your actual project path
- Use double backslashes (`\\`) in JSON for Windows paths
- Requires Claude Desktop version 0.7.0+ (MCP support)

#### 3. Restart Claude Desktop

Close Claude Desktop completely (check system tray) and restart it. The MCP server should now be connected.

#### 4. Verify Connection

In Claude Desktop, you should see:
- MCP server indicator showing "Connected" status
- "canary-mcp-server" listed in available servers
- Available tools in the interface

#### 5. Use the MCP Tools

You can now interact with Canary Historian data using natural language:

```
"Use the list_namespaces tool to show me available Canary namespaces"

"Use the search_tags tool to find all temperature sensors"

"Use the read_timeseries tool to get data for tag 'Secil.Line1.Temperature'
from yesterday to now"

"Use the get_server_info tool to check the Canary server connection"
```

#### Available MCP Tools

- **`ping`** - Test MCP server connection
- **`list_namespaces`** - Browse Canary hierarchical structure
- **`search_tags`** - Find tags by pattern matching
- **Tip:** When using `search_tags`, provide the literal identifier (for example `P431`) without appending wildcard characters—the Canary API handles fuzzy matching internally.
- **`get_tag_metadata`** - Get detailed tag information
- **`get_tag_properties`** - Retrieve raw engineering properties and historian metadata for tags
- **`read_timeseries`** - Query historical time-series data
- **`get_server_info`** - Check Canary server health and info

**Detailed Setup Guide:** See [docs/installation/claude-desktop-setup.md](docs/installation/claude-desktop-setup.md)

## Configuration

Configuration is managed through environment variables. Copy `.env.example` to `.env` and customize:

```bash
# Required: Canary API Configuration
CANARY_SAF_BASE_URL=https://scunscanary.secil.pt/api/v1
CANARY_VIEWS_BASE_URL=https://scunscanary.secil.pt
CANARY_API_TOKEN=your-token-here
CANARY_TAG_SEARCH_ROOT=Secil.Portugal
CANARY_TAG_SEARCH_FALLBACKS=
CANARY_LAST_VALUE_LOOKBACK_HOURS=24
CANARY_LAST_VALUE_PAGE_SIZE=500


# Optional: Server Configuration
MCP_SERVER_HOST=localhost
MCP_SERVER_PORT=6000

# Optional: Logging
LOG_LEVEL=INFO

# Optional: Performance Settings
CANARY_TIMEOUT=30
CANARY_POOL_SIZE=10
CANARY_RETRY_ATTEMPTS=6
```

**Key Configuration Variables:**

- **`CANARY_SAF_BASE_URL`** - Base URL for Canary SAF (Store and Forward) API
- **`CANARY_VIEWS_BASE_URL`** - Base URL for Canary Views API
- **`CANARY_API_TOKEN`** - Authentication token (required, keep secret!)
- **`CANARY_TAG_SEARCH_ROOT`** - Root namespace used when calling `browseTags` (for example `Secil.Portugal`)
- **`CANARY_TAG_SEARCH_FALLBACKS`** - Additional namespace prefixes (comma-separated) to probe when the root scope is empty
- **`CANARY_LAST_VALUE_LOOKBACK_HOURS`** - Window (hours) used when retrieving last known values
- **`CANARY_LAST_VALUE_PAGE_SIZE`** - Maximum samples requested to resolve last values
- **`LOG_LEVEL`** - Logging verbosity: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **`CANARY_TIMEOUT`** - Request timeout in seconds (default: 30)
- **`CANARY_RETRY_ATTEMPTS`** - Number of retry attempts for failed requests (default: 6)

See `.env.example` for the complete list of available configuration options including performance tuning, circuit breaker settings, and session management.

## Documentation

Comprehensive documentation is available in the `docs/` directory:

### API Reference

**[API Documentation (docs/API.md)](docs/API.md)** - Complete reference for all MCP tools:
- **Core Data Access Tools**: search_tags, get_tag_metadata, read_timeseries, list_namespaces, get_server_info
- **Performance & Monitoring Tools**: get_metrics, get_metrics_summary
- **Cache Management Tools**: get_cache_stats, invalidate_cache, cleanup_expired_cache
- **Error Codes**: Authentication, connection, timeout, circuit breaker errors
- **Best Practices**: Caching strategy, performance optimization, query patterns

### Example Queries

**[Example Query Library (docs/examples.md)](docs/examples.md)** - 20+ real-world examples covering:
- **Validation Use Cases**: Sensor validation, cross-validation, data quality checks
- **Troubleshooting Use Cases**: Anomaly diagnosis, pattern identification, performance comparison
- **Optimization Use Cases**: Operating setpoint optimization, energy waste detection, stability analysis
- **Reporting Use Cases**: Daily reports, compliance reporting, shift handovers
- **Integration Examples**: Maintenance alerts, predictive maintenance, energy management

### Additional Documentation

- **[Deployment Guide](docs/DEPLOYMENT.md)** - Complete site rollout and deployment procedures
- **[Architecture](docs/architecture.md)** - System architecture and design decisions
- **[Multi-Site Configuration](docs/multi-site-config.md)** - Managing multiple Canary sites
- **[Troubleshooting Guide](docs/troubleshooting/)** - Common issues and solutions
- **[PRD & Epics](docs/PRD.md)** - Product requirements and feature planning

### Quick Links

```
"Find all temperature sensors for Kiln 6"
→ See examples.md: Example 1 (Sensor Validation)

"Show me performance from yesterday"
→ See examples.md: Example 6 (Historical Comparison)

"What tools are available?"
→ See API.md: Core Data Access Tools
```

## Development

### Project Structure

- **src/canary_mcp/** - Main application code
- **tests/** - Test suite (unit and integration)
- **docs/** - Documentation (PRD, epics, stories)
- **config/** - Configuration files

### Development Workflow

1. **Install hooks once**: `pre-commit install` (adds Ruff, Black, and isort to every commit per Story 4.7). No TypeScript lives in this repo yet, so ESLint/Prettier will be added when a TS package appears.
2. **Before each PR** (quick checklist):
   1. `pre-commit run --all-files`
   2. `uv run pytest -m "unit or not integration" -q`
   3. `uv run pytest -m integration -q` *(requires `CANARY_*` creds)*
   4. `uv run pytest --cov=canary_mcp --cov-report=term --cov-report=html --cov-report=json:coverage.json`
   5. `python scripts/ci/check_coverage.py coverage.json --baseline-file docs/coverage-baseline.json`
   6. Open `htmlcov/index.html` to inspect changed modules.

See [docs/development/testing-and-coverage.md](docs/development/testing-and-coverage.md) for the expanded playbook, CI job matrix, and guidance on updating the coverage baseline.

### Adding New MCP Tools

```python
# In src/canary_mcp/server.py

@mcp.tool()
def your_tool_name(parameter: str) -> str:
    """
    Tool description for LLM clients.

    Args:
        parameter: Parameter description

    Returns:
        str: Return value description
    """
    # Implementation
    return "result"
```

## Project Status

All planned epics are complete. The MCP server now ships with:
- Canary authentication, namespace browsing, tag search, metadata, and timeseries tools
- Remote deployment playbooks (Windows & Linux) plus container images
- Client onboarding guides and health-check automation

## Roadmap

### ✅ Epic 1 - Story 1.1 (Current)
- [x] Python 3.13 project with uv
- [x] FastMCP SDK integration
- [x] Basic server with ping tool
- [x] Testing framework (73% coverage)
- [x] Project documentation

### ✅ Epic 1 - Remaining Stories
- [x] Story 1.2: Canary API Authentication & Session Management
- [x] Story 1.3: list_namespaces Tool & Validation
- [x] Story 1.4: search_tags Tool & Validation
- [x] Story 1.5: get_tag_metadata Tool & Validation
- [x] Story 1.6: read_timeseries Tool & Validation
- [x] Story 1.7: get_server_info Tool & Validation
- [x] Stories 1.8-1.11: Testing, error handling, installation, dev environment

### ✅ Epic 2 - Production Hardening
- [x] Performance optimization (caching, connection pooling)
- [x] Advanced error handling
- [x] Multi-site configuration
- [x] Comprehensive documentation

### ✅ Epic 3 - MVP
- [x] Epic 3 - Advanced Features (Future)

## Testing
### Coverage

Generate the latest coverage reports with:
```bash
uv run pytest --cov=canary_mcp --cov-report=term --cov-report=html --cov-report=json:coverage.json
python scripts/ci/check_coverage.py coverage.json --baseline-file docs/coverage-baseline.json
```

- `htmlcov/index.html` → drill into individual files/lines.
- `scripts/ci/check_coverage.py` enforces Story 4.7’s policy (warn if repo coverage <75 %, fail if regression >5 pp vs `docs/coverage-baseline.json`).
- CI/CD tip: run the two commands above and treat the script’s warning output (`[coverage] WARNING: overall coverage 73% ...`) as a non-blocking signal; only regressions >5 pp trigger a non-zero exit code.

> Note: automated coverage collection may require Python to be available on PATH inside your environment. If the command fails (for example on Windows Subsystem for Linux without Python), install Python 3.12+ or use the project virtual environment (`.venv/Scripts/python.exe -m pytest ...`).

### Test Categories

- **Unit Tests** (`tests/unit/`) - Fast, isolated component tests
- **Integration Tests** (`tests/integration/`) - Server startup and tool invocation tests
- **Contract Tests** (Future) - API contract validation

## Contributing

This is a hackathon project developed following the BMM (BMAD Meta-Method) workflow. See `docs/` for:
- `PRD.md` - Product Requirements Document
- `epics.md` - Epic and story breakdown
- `stories/` - Individual story implementation plans

## License

See [LICENSE](LICENSE) file.

## Support

For questions or issues:
1. **[API Documentation](docs/API.md)** - Complete tool reference with error codes
2. **[Example Query Library](docs/examples.md)** - 20+ real-world use cases
3. **[Troubleshooting Guide](docs/troubleshooting/)** - Common issues and solutions
4. Review test files for usage examples (`tests/integration/`)
5. Canary API docs: https://readapi.canarylabs.com/25.4/

---

**Generated with** [Claude Code](https://claude.com/claude-code)
**MCP Protocol:** https://modelcontextprotocol.io/
