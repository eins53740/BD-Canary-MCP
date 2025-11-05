# Secil Canary Historian MCP Server

Model Context Protocol (MCP) server providing seamless access to Canary Historian plant data for LLM-powered applications.

## Overview

The Universal Canary MCP Server enables LLM clients (Claude Desktop, Continue, etc.) to interact with Canary Historian industrial data through natural language queries. This server implements the MCP protocol standard, exposing tools that allow engineers and analysts to access real-time and historical plant data without manual API integration.

**Project Status:** MVP implemented | Secil Cement Maceira site supported | Mortars Supported | Outão site ongoing

## Features

- ✅ **MCP Protocol Implementation** - FastMCP-based server with tool registration
- ✅ **Ping Tool** - Connection testing and health check
- ✅ **Environment Configuration** - Flexible configuration via environment variables
- ✅ **Local Tag Dictionary** - Offline index seeded from Canary exports keeps natural-language tag mapping reliable even when API search misses
- ✅ **Auto Tag Resolution** - Short identifiers (for example `P431`) transparently resolve to fully-qualified Canary paths across all tools
- ✅ **Comprehensive Testing** — Unit/integration suites plus automated health checks
- ✅ **Canary API Integration** - Coming in Story 1.2
- ✅ **Data Access Tools** - Coming in Stories 1.3-1.7

## MCP Server Capabilities

The Canary MCP Server exposes a rich set of capabilities for interacting with the Canary Historian. These are categorized into Tools, Prompts (Workflows), and Resources.

### Access Control

Access to the MCP server is secured using OAuth 2.0, the industry-standard protocol for authorization. MCP clients must present a valid bearer token to access the server's resources.

#### Canary API Authentication

Authentication to the underlying Canary API is handled transparently by the server. The `CANARY_API_TOKEN` environment variable must be set with a valid API token, which the server uses for all communication with the Canary Historian.

### Tools

Tools are functions that can be directly executed by an MCP client.

*   **`ping()`**: A simple tool to check if the MCP server is running and responsive. Returns a "pong" message.
*   **`get_asset_catalog()`**: Retrieves curated metadata for sensors and tags from the local asset catalog. This is useful for getting an overview of available tags without querying the live server.
*   **`search_tags(search_pattern)`**: Searches for tags in the Canary Historian that match a given pattern.
*   **`get_tag_metadata(tag_path)`**: Retrieves detailed metadata for a specific, fully qualified tag path.
*   **`get_tag_path(description)`**: Resolves a natural-language description into the most likely tag path by searching the catalog and live server.
*   **`get_tag_properties(tag_paths)`**: Fetches the raw, detailed property dictionaries for a list of tag paths.
*   **`list_namespaces()`**: Lists the available tag namespaces (hierarchical folders) in the Canary Historian.
*   **`get_last_known_values(tag_names)`**: Retrieves the most recent data point for one or more tags.
*   **`read_timeseries(tag_names, start_time, end_time)`**: Queries for historical time-series data for one or more tags within a specified time range.
*   **`get_server_info()`**: Gets health and capability information from the Canary server, including supported timezones and aggregates.
*   **`get_metrics()`**: Returns detailed performance metrics for the MCP server in Prometheus format.
*   **`get_metrics_summary()`**: Returns a human-readable summary of the server's performance metrics.
*   **`get_cache_stats()`**: Provides statistics on the server's internal cache performance.
*   **`invalidate_cache(pattern)`**: Invalidates cache entries, optionally filtered by a key pattern.
*   **`cleanup_expired_cache()`**: Manually triggers a cleanup of expired cache entries.
*   **`get_health()`**: Returns the overall health status of the MCP server, including the state of its circuit breakers.

### Prompts (Workflows)

Prompts are structured, multi-step workflows that guide an LLM or MCP client through a complex process.

*   **`tag_lookup_workflow`**: A guided workflow for translating a natural-language request (e.g., "the main kiln temperature") into a precise Canary tag path. It orchestrates the use of `get_asset_catalog`, `search_tags`, and `get_tag_properties`.
*   **`timeseries_query_workflow`**: A workflow for safely and efficiently retrieving historical data. It guides the user to first resolve tag names, then define time ranges, and finally call `read_timeseries` with appropriate parameters.

### Resources

Resources provide static data or documentation to the MCP client to aid in constructing valid queries.

*   **`maceira_tag_catalog`**: A JSON resource containing the curated list of tags for the Maceira site, including natural-language descriptions and engineering units. This is the primary reference for tag discovery.
*   **`canary_time_standards`**: A JSON resource that provides a reference guide for Canary's relative time expressions (e.g., "Now-1d") and the server's default timezone (`Europe/Lisbon`).

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

# Run integration tests only
uv run pytest -m integration -q

# Run with coverage
uv run pytest --cov=. --cov-report=term-missing -q
```

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

1. Make changes to source code
2. Run tests: `uv run pytest`
3. Check linting: `uvx ruff check .`
4. Format code: `uvx black .`
5. Verify coverage: `uv run pytest --cov=. --cov-report=term-missing`

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

Generate the latest coverage report with:
```bash
uv run pytest --cov=src --cov-report=term
```

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
