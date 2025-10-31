# Universal Canary MCP Server

Model Context Protocol (MCP) server providing seamless access to Canary Historian plant data for LLM-powered applications.

## Overview

The Universal Canary MCP Server enables LLM clients (Claude Desktop, Continue, etc.) to interact with Canary Historian industrial data through natural language queries. This server implements the MCP protocol standard, exposing tools that allow engineers and analysts to access real-time and historical plant data without manual API integration.

**Project Status:** Story 1.1 Complete - Foundation & Protocol Implementation

## Features

- ✅ **MCP Protocol Implementation** - FastMCP-based server with tool registration
- ✅ **Ping Tool** - Connection testing and health check
- ✅ **Environment Configuration** - Flexible configuration via environment variables
- ✅ **Comprehensive Testing** - Unit and integration tests with 73% coverage
- 🚧 **Canary API Integration** - Coming in Story 1.2
- 🚧 **Data Access Tools** - Coming in Stories 1.3-1.7

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

### Prerequisites

- **Python 3.12+** (3.13 recommended)
- **uv** - Fast Python package manager ([install guide](https://docs.astral.sh/uv/))
- **Git** - For cloning the repository

### Setup Steps

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd BD-hackaton-2025-10
   ```

2. **Install dependencies:**
   ```bash
   uv sync --all-extras
   ```

   This installs:
   - `fastmcp` - MCP SDK
   - `httpx` - HTTP client for Canary API (future use)
   - `python-dotenv` - Environment configuration
   - `pytest` and dev tools

3. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Verify installation:**
   ```bash
   uv run pytest -v
   ```

   Expected output: All tests passing ✅

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

## Configuration

Configuration is managed through environment variables. Copy `.env.example` to `.env` and customize:

```bash
# Canary API Configuration (Story 1.2+)
CANARY_API_URL=https://your-canary-server/api
CANARY_API_TOKEN=your-token-here

# Server Configuration
MCP_SERVER_HOST=localhost
MCP_SERVER_PORT=3000

# Logging
LOG_LEVEL=INFO
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

## Roadmap

### ✅ Epic 1 - Story 1.1 (Current)
- [x] Python 3.13 project with uv
- [x] FastMCP SDK integration
- [x] Basic server with ping tool
- [x] Testing framework (73% coverage)
- [x] Project documentation

### 🚧 Epic 1 - Remaining Stories
- Story 1.2: Canary API Authentication & Session Management
- Story 1.3: list_namespaces Tool & Validation
- Story 1.4: search_tags Tool & Validation
- Story 1.5: get_tag_metadata Tool & Validation
- Story 1.6: read_timeseries Tool & Validation
- Story 1.7: get_server_info Tool & Validation
- Stories 1.8-1.11: Testing, error handling, installation, dev environment

### 🎯 Epic 2 - Production Hardening (Future)
- Performance optimization (caching, connection pooling)
- Advanced error handling
- Multi-site configuration
- Comprehensive documentation

## Testing

### Test Coverage

Current coverage: **73%**
Target: **75%+** (NFR003)

```bash
# Generate detailed coverage report
uv run pytest --cov=src --cov-report=html
# Open htmlcov/index.html in browser
```

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
1. Check `docs/` for detailed documentation
2. Review test files for usage examples
3. See Canary API docs: https://readapi.canarylabs.com/25.4/

---

**Generated with** [Claude Code](https://claude.com/claude-code)
**MCP Protocol:** https://modelcontextprotocol.io/
