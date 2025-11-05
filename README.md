# Universal Canary MCP Server

Model Context Protocol (MCP) server providing seamless access to Canary Historian plant data for LLM-powered applications.

## Overview

The Universal Canary MCP Server enables LLM clients (Claude Desktop, Continue, etc.) to interact with Canary Historian industrial data through natural language queries. This server implements the MCP protocol standard, exposing tools that allow engineers and analysts to access real-time and historical plant data without manual API integration.

**Project Status:** Story 1.1 Complete - Foundation & Protocol Implementation

## Features

- ✅ **MCP Protocol Implementation** - FastMCP-based server with tool registration
- ✅ **Ping Tool** - Connection testing and health check
- ✅ **Environment Configuration** - Flexible configuration via environment variables
- ✅ **Local Tag Dictionary** - Offline index seeded from Canary exports keeps natural-language tag mapping reliable even when API search misses
- ✅ **Auto Tag Resolution** - Short identifiers (for example `P431`) transparently resolve to fully-qualified Canary paths across all tools
- ✅ **Comprehensive Testing** — Unit/integration suites plus automated health checks
- ✅ **Canary API Integration** - Coming in Story 1.2
- ✅ **Data Access Tools** - Coming in Stories 1.3-1.7

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
│  │  - [Future: Canary data tools]    │  │
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

## Installation

The Canary MCP Server supports two installation methods to accommodate different user needs and environments. Choose the method that best fits your situation.

### Installation Options Overview

| Feature | Non-Admin Windows | Docker |
|---------|------------------|--------|
| **Administrator Privileges** | Not required | Required (for Docker Desktop) |
| **Installation Time** | 10-15 minutes | 5-10 minutes |
| **Environment Isolation** | Process-level | Complete containerization |
| **Reproducibility** | Depends on host configuration | Identical across environments |
| **Resource Usage** | Lower (native process) | Higher (Docker overhead) |
| **Updates** | Update packages with `uv` | Rebuild Docker image |
| **Best For** | Company workstations, dev laptops | Production, DevOps workflows |
| **Configuration** | `.env` file in project root | `.env` file + Docker Compose |

### When to Use Each Method

**Choose Non-Admin Windows Installation if:**
- You work on a company workstation without administrator privileges
- You want minimal resource overhead
- You prefer native Python development workflow
- You need quick setup without Docker dependencies

**Choose Docker Installation if:**
- You have Docker Desktop access
- You need reproducible deployments across environments
- You want complete environment isolation
- You're deploying to production or staging environments
- You're already using containerization in your workflow

### Quick Start Guides

#### Option 1: Non-Admin Windows Installation (Recommended for Workstations)

For users without administrator privileges on Windows workstations.

**Prerequisites:**
- No administrator privileges required
- Internet access to download Python and uv

**Quick Setup:**
```bash
# 1. Install Python 3.13 portable (download from python.org)
# 2. Install uv package manager
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 3. Clone repository
git clone <repository-url>
cd BD-hackaton-2025-10

# uv
uv sync
uv sync --locked --all-extras --dev

# 4. Install MCP server (user-space)
uv pip install -e .

# 5. Configure environment
copy .env.example .env
# Edit .env with your Canary credentials

# 6. Validate installation
python scripts/validate_installation.py

# 7. Start server
python -m canary_mcp.server
```

**Detailed Guide:** See [docs/installation/non-admin-windows.md](docs/installation/non-admin-windows.md)

**Troubleshooting:** See [docs/installation/troubleshooting.md](docs/installation/troubleshooting.md)

#### Option 2: Docker Installation (Recommended for Production)

For users with Docker Desktop access, ideal for production deployments.

**Prerequisites:**
- Docker Desktop installed (requires admin for installation)
- Docker Compose (included with Docker Desktop)
- At least 4GB RAM allocated to Docker
- 2GB free disk space

**Quick Setup:**
```bash
# 1. Clone repository
git clone <repository-url>
cd BD-hackaton-2025-10

# 2. Configure environment
copy .env.example .env
# Edit .env with your Canary credentials

# 3. Build Docker image
docker build -t canary-mcp-server .

# 4. Start container
docker-compose up -d

# 5. Verify container is running
docker-compose ps

# 6. View logs
docker-compose logs -f
```

**Detailed Guide:** See [docs/installation/docker-installation.md](docs/installation/docker-installation.md)

### Installation Validation

After installation, verify your setup with the validation script:

```bash
python scripts/validate_installation.py
```

This script checks:
- Python version (>= 3.13)
- uv package manager installation
- canary-mcp package installation
- Required dependencies (fastmcp, httpx, python-dotenv, structlog)
- Configuration file (.env) exists and valid
- Server can start without errors
- Logs directory is writable

## Usage

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
MCP_SERVER_PORT=3000

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
