# Secil Canary MCP Server - Simplified Guide

A lightweight and practical guide for setting up, running, and using the **Canary MCP Server** to access plant data through natural language queries.

---

## 🚀 Overview

The **Canary MCP Server** connects **LLM-powered clients** (e.g. Claude Desktop) to **Canary Historian** plant data. It lets engineers and analysts explore data, run queries, and fetch timeseries without manual API calls.

**Status:** MVP ready → Maceira and Mortars sites supported → Outão in progress

---

## ⚙️ Features at a Glance

- MCP Protocol with FastMCP integration
- Canary Historian API (read/write)
- Offline tag dictionary for reliable NL lookups
- Auto tag resolution (e.g. `P431` → full Canary path)
- Health check tools and local cache
- Supports STDIO (local) and HTTP (remote)

---

## 🧩 Installation 1/2

### Option 1: Local Setup (STDIO)
Best for individual use — **no admin rights needed**.

```bash

# Install Python 3.14
https://www.python.org/downloads/release/python-3140/

# Install uv (one-time)
# Windows PowerShell
Set-ExecutionPolicy Bypass -Scope Process -Force
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
$env:Path += ";$env:USERPROFILE\.local\bin"
uv --version # To confirm uv is up and running. You may reboot your terminal

# Clone repository
 git clone https://secil.ghe.com/secil-uns-ot/CanaryMCP
 cd CanaryMCP

# Create environment
 uv sync --locked

# Copy and edit .env
 copy .env.example .env
 notepad .env  # add your CANARY_API_TOKEN (Call UNS-OT DT Team)

# Validate installation
 uv run python scripts/validate_installation.py #Nota -> da sempre erro no python-dotenv...

# Run server
 uv run canary-mcp

# Configure Claude Desktop
#Note: You may close the MCP server. Claude Desktop will restart it as needed.


```

Validation success message:
> "pong – Canary MCP Server is running!"

If ping fails, rerun installer with `--verbose` or check `docs/troubleshooting/DEBUG_MCP_SERVER.md`.

### Option 2: Remote Deployment (HTTP/SSE)
### Option 3: Containerized (Docker / Podman)

---
## 💬 Connecting to Claude Desktop (+Installation) 2/2

The primary way to use this MCP server is through Claude Desktop. Follow these steps to connect:

0. Install Claude Desktop (or other LLM chat with MCP clients features)
https://claude.ai/redirect/claudedotcom.v1.60777239-e2d4-4d6b-bd2e-0f9ebd82b555/api/desktop/win32/x64/exe/latest/redirect


1. Locate your config file (or create a new one):
   ```
   %APPDATA%\Claude\claude_desktop_config.json
   ```
2. Add MCP server configuration:
   ```json
		{
		  "mcpServers": {
			"canary-mcp-server": {
			  "command": "uv",
			  "args": [
				"--directory",
				"C:\\Github\\MCPServer",
				"run",
				"python",
				"-m",
				"canary_mcp.server"
			  ],
			  "env": {
				"PYTHONPATH": "C:\\Github\\MCPServer\\src"
			  }
			}
		  }
		}
   ```
   
   **Important Notes:**
	- Replace `C:\\Github\\MCPServer` with your actual project path
	- Use double backslashes (`\\`) in JSON for Windows paths
	- Requires Claude Desktop version 0.7.0+ (MCP support)


3. Restart Claude Desktop and check that the server shows as **Connected**.

Try it out:
```
Use the search_tags tool to find kiln temperature sensors.
```

---

## 🧠 Key MCP Tools

| Tool | Description |
|------|--------------|
| `ping()` | Check connection to the MCP server |
| `list_namespaces()` | List available Canary namespaces |
| `search_tags(pattern)` | Find tags matching a pattern |
| `get_tag_metadata(path)` | Fetch metadata (units, description, etc.) |
| `read_timeseries(tag, start, end)` | Retrieve historical data |
| `get_server_info()` | Display system and API info |
| `get_metrics()` | Show usage metrics and health summary |

> Tip: When searching tags, use short names (like `P431`); the server resolves them automatically.

---

## 🔐 Configuration

Edit `.env` file:

```ini
CANARY_SAF_BASE_URL=https://scunscanary.secil.pt/api/v1
CANARY_VIEWS_BASE_URL=https://scunscanary.secil.pt
CANARY_API_TOKEN=<your-token>
CANARY_MCP_TRANSPORT=stdio
LOG_LEVEL=INFO
```

Common settings:
- `CANARY_DEFAULT_VIEW` → Default Canary view (e.g. `Secil.Portugal.Default`)
- `CANARY_TIMEOUT` → Default 30s
- `CANARY_POOL_SIZE` → Default 10

---

## 🧪 Testing and Validation

```bash
# Run ping test
uv run python -m canary_mcp.server

# Run tests
uv run pytest

# Example CLI tests
python scripts/run_get_metrics.py
python scripts/run_get_health.py
```

---

## 🧰 Troubleshooting

- If environment variables aren’t loaded → ensure `.env` exists and `python-dotenv` is installed.
- If Canary API returns 401 → check token validity.
- If connection fails → validate transport (STDIO vs HTTP) and firewall rules.

---

## 🗺️ Folder Overview

```
CanaryMCP/
├── src/canary_mcp/        # MCP Server code
├── tests/                 # Unit & integration tests
├── docs/                  # Documentation
├── scripts/               # Helper & validation scripts
└── .env.example            # Environment template
```

---

## 📚 Docs & References

- [API Reference](docs/API.md)
- [Examples Library](docs/examples.md)
- [Deployment Guide](docs/installation/DEPLOYMENT.md)
- [Troubleshooting](docs/troubleshooting/)

---

## ✅ Summary

The Secil Canary MCP Server bridges LLM clients and industrial data sources, allowing safe, natural-language access to historian data. It supports local or remote deployment, integrates easily with Claude Desktop, and includes health monitoring, caching, and extensive developer tools.

---

**Author:** Secil UNS Platform Team  
**Version:** MVP (Nov 2025)  
**License:** See `LICENSE`
