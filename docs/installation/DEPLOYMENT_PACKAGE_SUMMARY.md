# Canary MCP Server Deployment Package Summary

This summary replaces legacy rollout notes and captures the three supported installation paths for the Canary MCP server. Each option reaches the same feature set; choose the path that best matches your environment.

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
