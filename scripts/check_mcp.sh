#!/usr/bin/env bash
set -euo pipefail

mode="${1:-stdio}"
target="${2:-http://localhost:6000}"

if [[ "${mode}" == "stdio" ]]; then
  echo "[check] starting MCP server in stdio mode"
  uv run python -m canary_mcp.server --health-check
else
  echo "[check] querying HTTP MCP endpoint: ${target}"
  response="$(curl -fsS "${target%/}/mcp/v1/health")"
  status="$(python -c 'import json,sys; data=json.load(sys.stdin); print(data.get("status","unknown")); sys.exit(0 if data.get("status") not in {"unhealthy", "offline"} else 1)' <<< "${response}")"
  echo "[check] remote status: ${status}"
fi

echo "MCP configuration OK: ${mode}"
