# Canary MCP Server Deployment Package Summary

This summary replaces legacy rollout notes and captures the three supported installation paths for the Canary MCP server. Each option reaches the same feature set; choose the path that best matches your environment.

---

## Quick Start (Per MCP Server)

Non-technical steps to launch the server and validate first run.

- Supported OS: Windows 10/11, macOS 12+, Linux (x86_64)
- Prerequisites: Python 3.12+, uv installed, outbound HTTPS access, optional: Docker
- Ports (HTTP mode only): default 6000/TCP
- Environment: copy .env.example to .env and set CANARY_* variables

Steps (STDIO mode, local dev):
```bash
# from repo root
uv sync --locked --dev
copy .env.example .env  # on Windows (or: cp .env.example .env on macOS/Linux)
uv run canary-mcp
```
Expected output:
- Logs show server startup; ping tool responds.

Steps (HTTP SSE mode):
```bash
# from repo root
set CANARY_MCP_TRANSPORT=http & set CANARY_MCP_HOST=0.0.0.0 & set CANARY_MCP_PORT=6000  # Windows cmd
# macOS/Linux: export CANARY_MCP_TRANSPORT=http; export CANARY_MCP_HOST=0.0.0.0; export CANARY_MCP_PORT=6000
uv run canary-mcp
```
Validation:
```bash
# STDIO (MCP Inspector)
npx @modelcontextprotocol/inspector uv --directory . run canary-mcp

# HTTP (health endpoint via curl)
curl -fsS http://localhost:6000/mcp/v1/health
```
Troubleshooting:
- "Module not found": ensure uv sync ran successfully and PYTHONPATH not overridden.
- Port in use: change CANARY_MCP_PORT.
- 401/403 via proxy: add required auth headers at the proxy.

---

## Quick Start (Per MCP Client)

Run a client and verify connectivity to the server.

- Clients: Claude Desktop (stdio), MCP Inspector (stdio), HTTP SSE clients
- Prerequisites: matching transport and URL/command

Claude Desktop (STDIO):
```json
{
  "mcpServers": {
    "canary-mcp-local": {
      "command": "uv",
      "args": ["run", "python", "-m", "canary_mcp.server"],
      "transport": "stdio"
    }
  }
}
```
Verification: Restart Claude Desktop; tools list should show Canary MCP; run ping tool.

MCP Inspector (STDIO):
```bash
npx @modelcontextprotocol/inspector uv --directory . run canary-mcp
```

HTTP SSE client example (generic):
```json
{
  "mcpServers": {
    "canary-mcp-remote": {
      "url": "http://localhost:6000/",
      "transport": "sse"
    }
  }
}
```
Validation:
- STDIO: Inspector UI opens; server logs show session.
- HTTP: curl http://localhost:6000/mcp/v1/health returns healthy JSON.

Troubleshooting:
- STDIO not launching: confirm uv on PATH; try uv run python -m canary_mcp.server.
- HTTP blocked: open firewall or use different port; confirm reverse proxy if present.

---

## Installers

Status: Platform-native installers are not yet produced in this repository.

- Windows (.exe/.msi): Not available. Use uv + Python or Docker.
- macOS (.pkg/notarised .app): Not available. Use uv + Python or Docker.
- Linux (.deb/.rpm/AppImage): Not available. Use uv + Python or Docker.

Locations (when available):
- docs/installation/installers/ (planned)

Run instructions (planned):
- Windows: CanaryMCPSetup.msi /qn
- macOS: sudo installer -pkg CanaryMCP.pkg -target /
- Linux deb: sudo dpkg -i canary-mcp_<ver>_amd64.deb
- Linux rpm: sudo rpm -Uvh canary-mcp-<ver>.x86_64.rpm

Uninstall (planned):
- Windows: msiexec /x {PRODUCT_CODE}
- macOS: sudo /usr/local/bin/canary-mcp-uninstall
- Linux deb: sudo apt remove canary-mcp
- Linux rpm: sudo dnf remove canary-mcp

Build instructions (to implement):
- Create platform installers via PyInstaller + fpm/wixtoolset/notarization pipelines.
- Document exact build scripts under scripts/packaging/ and update this section with commands and artifact paths.

---

## 1. Installation Options

### 1.1 Local MCP Server (STDIO)
- **Use when** you want a developer-friendly, single-machine setup with minimal networking requirements.
- **Transport**: STDIO (default in `.env` – `CANARY_MCP_TRANSPORT=stdio`).
- **Startup**:
  ```bash
  uv run python -m canary_mcp.server
  ```
- **Clients** communicate over STDIO pipes (Claude Desktop, Continue, etc.).
- **Notes**: Ideal for testing new features or when the MCP client and server run on the same workstation.

### 1.2 HTTP SSE MCP Server
- **Use when** multiple users need to share a central server or you are deploying to an internal VM (for example `vmhost8.secil.pt`).
- **Transport**: HTTP with Server-Sent Events (`CANARY_MCP_TRANSPORT=http`).
- **Key `.env` entries**:
  ```
  CANARY_MCP_TRANSPORT=http
  CANARY_MCP_HOST=0.0.0.0
  CANARY_MCP_PORT=6000
  ```
- **Startup**:
  ```bash
  uv run python -m canary_mcp.server
  ```
- **Docs**: See `docs/installation/REMOTE_HTTP_DEPLOYMENT.md` for Linux and Windows Server runbooks, including reverse-proxy guidance and systemd/NSSM service setup.

### 1.3 HTTP SSE MCP Server in Containers (Docker/Podman)
- **Use when** you need immutable builds, CI/CD integration, or managed infrastructure.
- **Assets**: `Dockerfile`, `docker-compose.yml`, and Podman equivalents.
- **Quick start**:
  ```bash
  docker compose up --build
  # or
  podman-compose up --build
  ```
- **Configuration**: Provide `.env` via bind mount or environment injection. Container entrypoint already honours `CANARY_MCP_TRANSPORT=http`.
- **Notes**: Works well behind corporate ingress (NGINX, Traefik, etc.) and in orchestrators that support SSE (Kubernetes, Nomad).

---

## 2. Configuring MCP Clients (Claude Desktop Examples)

### 2.1 Local MCP (STDIO)
```json
{
  "mcpServers": {
    "canary-mcp-local": {
      "command": "uv",
      "args": ["run", "python", "-m", "canary_mcp.server"],
      "transport": "stdio"
    }
  }
}
```
- Runs the server alongside Claude Desktop on the same machine.
- Adjust `command`/`args` to match your runtime (e.g., direct path to `python.exe`).

### 2.2 Remote MCP (HTTP SSE)
```json
{
  "mcpServers": {
    "canary-mcp-remote": {
      "url": "http://vmhost8.secil.pt:6000/",
      "transport": "sse"
    }
  }
}
```
- Point to your corporate URL (use `https://` when fronted by TLS).
- Add headers or tokens in the JSON if the reverse proxy enforces auth.

---

## 3. Verification Script

A minimal health-check script is available at `scripts/check_mcp.sh`. It validates both STDIO and HTTP SSE deployments.

```bash
#!/usr/bin/env bash
set -euo pipefail

mode="${1:-stdio}"

if [[ "${mode}" == "stdio" ]]; then
  echo "[check] starting MCP server in stdio mode"
  uv run python -m canary_mcp.server --health-check
else
  target="${2:-http://vmhost8.secil.pt:6000}"
  echo "[check] querying HTTP MCP endpoint: ${target}"
  curl -fsS "${target}/mcp/v1/health" | jq '.status'
fi

echo "MCP configuration OK: ${mode}"
```

### Expected Output
- **STDIO**: Console prints the health result and exits 0.
- **HTTP SSE**: `curl` prints `"healthy"` (or similar) from the JSON response.

### Common Failure Modes
- **Port closed**: `curl: (7) Failed to connect` – open the firewall or adjust reverse proxy.
- **Auth required**: HTTP 401/403 – ensure headers or tokens are supplied.
- **Missing binary**: STDIO mode fails if `uv`/`python` are not on PATH.
- **Invalid transport**: Check `.env` values; comments inline with values can break parsing.

Run `./scripts/check_mcp.sh stdio` locally or `./scripts/check_mcp.sh http http://<host>:<port>` after remote deployment.

---

## 4. Next Steps

- Use the option that best matches your rollout (local development, shared VM, or containers).
- Follow `docs/installation/REMOTE_HTTP_DEPLOYMENT.md` for detailed remote instructions.
- Reference `docs/installation/docker-installation.md` and `docs/installation/non-admin-windows.md` for the corresponding setup walkthroughs.
