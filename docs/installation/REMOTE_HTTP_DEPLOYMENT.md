# Canary MCP Remote HTTP Deployment

This guide documents the migration of the Canary MCP server from local STDIO operation to a remotely hosted HTTP endpoint on `vmhost8.secil.pt`. The server continues to use native FastMCP transport, now exposed over HTTP so that all enterprise users can connect without local installations. Instructions cover both Linux (systemd) and Windows Server 2022 Standard environments.

## 1. Deployment Decisions
- **Transport**: FastMCP native HTTP transport (`CANARY_MCP_TRANSPORT=http`).
- **Host / Port**: Bind to `0.0.0.0:6000` (listen on all interfaces) unless you have a stricter requirement. Setting `CANARY_MCP_HOST` to `0.0.0.0` makes the service remotely reachable via any of the machine’s IP addresses. Use the actual server IP only if you want to restrict binding to a single interface.
- **Runtime**: Python 3.12 in a dedicated virtual environment, running under a service account.
- **Service Manager**: `systemd` on Linux; NSSM (or Task Scheduler) on Windows to provide Windows-service semantics.

---

## 2. Linux Deployment (systemd)

### 2.1 Prepare `vmhost8.secil.pt`
1. **Create service account**
   ```bash
   sudo useradd --system --create-home --shell /usr/sbin/nologin canarymcp
   sudo mkdir -p /opt/canary-mcp
   sudo chown canarymcp:canarymcp /opt/canary-mcp
   ```

2. **Install system dependencies**
   ```bash
   sudo apt-get update
   sudo apt-get install -y python3.12 python3.12-venv python3-pip build-essential
   ```

3. **Copy application bundle**
   - Build locally: `python -m build`.
   - Upload the wheel (`dist/canary_mcp-*.whl`) plus `.env`, `docs/aux_files/*` to `/tmp` on the VM (use `scp` or company artifact repo).
   - Move into place:
     ```bash
     sudo -u canarymcp cp /tmp/canary_mcp-*.whl /opt/canary-mcp/
     sudo -u canarymcp cp /tmp/.env /opt/canary-mcp/.env
     sudo chmod 600 /opt/canary-mcp/.env
     ```

4. **Create virtual environment**
   ```bash
   sudo -u canarymcp python3.12 -m venv /opt/canary-mcp/.venv
   sudo -u canarymcp /opt/canary-mcp/.venv/bin/pip install --upgrade pip
   sudo -u canarymcp /opt/canary-mcp/.venv/bin/pip install /opt/canary-mcp/canary_mcp-*.whl
   ```

5. **Populate auxiliary data** (needed by the new catalog resource)
   ```bash
   sudo -u canarymcp mkdir -p /opt/canary-mcp/docs/aux_files
   sudo -u canarymcp cp /tmp/Canary_Path_description_maceira.json /opt/canary-mcp/docs/aux_files/
   sudo -u canarymcp cp /tmp/maceira_postman_exampes.txt /opt/canary-mcp/docs/aux_files/
   ```

### 2.2 Environment Configuration
Update `/opt/canary-mcp/.env` (permissions 600) with production values:
```
CANARY_SAF_BASE_URL=https://<canary-saf-host>
CANARY_VIEWS_BASE_URL=https://<canary-views-host>
CANARY_TIMEZONE=Europe/Lisbon
CANARY_MCP_TRANSPORT=http
CANARY_MCP_HOST=0.0.0.0
CANARY_MCP_PORT=6000
CANARY_TAG_METADATA_PATH=/opt/canary-mcp/docs/aux_files/Canary_Path_description_maceira.json
CANARY_TAG_NOTES_PATH=/opt/canary-mcp/docs/aux_files/maceira_postman_exampes.txt
```
Add any credentials (Vault secrets, API keys) required by `CanaryAuthClient`. Ensure secrets are pulled via company mechanism; never hard-code them in the repo.

### 2.3 systemd Service
Create `/etc/systemd/system/canary-mcp.service`:
```ini
[Unit]
Description=Canary MCP HTTP Server
After=network.target

[Service]
Type=simple
User=canarymcp
Group=canarymcp
WorkingDirectory=/opt/canary-mcp
EnvironmentFile=/opt/canary-mcp/.env
ExecStart=/opt/canary-mcp/.venv/bin/python -m canary_mcp.server
Restart=on-failure
RestartSec=5
StandardOutput=append:/var/log/canary-mcp/server.log
StandardError=append:/var/log/canary-mcp/server.log

[Install]
WantedBy=multi-user.target
```

Finalize:
```bash
sudo mkdir -p /var/log/canary-mcp
sudo chown canarymcp:canarymcp /var/log/canary-mcp
sudo systemctl daemon-reload
sudo systemctl enable --now canary-mcp.service
sudo systemctl status canary-mcp.service
```

---

## 3. Windows Server 2022 Standard Deployment

### 3.1 Install prerequisites
1. **Create working directory and service account (optional but recommended)**
   ```powershell
   New-LocalUser -Name "canarymcp" -NoPassword
   Add-LocalGroupMember -Group "Users" -Member "canarymcp"
   New-Item -ItemType Directory -Path "C:\CanaryMCP" -Force | Out-Null
   ```
   Sign in as the service account (or use `runas`) for the remainder of the commands so files inherit the correct ownership.

2. **Install Python 3.12**
   - Download the Windows x64 installer from https://www.python.org/downloads/windows/.
   - Install for “All Users”, add Python to PATH, and enable the “pip” feature.

3. **Create virtual environment and install package**
   ```powershell
   cd C:\CanaryMCP
   python -m venv .venv
   .\.venv\Scripts\python -m pip install --upgrade pip
   # Copy the wheel built from CI or your dev machine to C:\CanaryMCP
   .\.venv\Scripts\python -m pip install .\canary_mcp-*.whl
   ```

4. **Copy auxiliary assets**
   ```powershell
   New-Item -ItemType Directory -Path "C:\CanaryMCP\docs\aux_files" -Force | Out-Null
   Copy-Item C:\temp\Canary_Path_description_maceira.json C:\CanaryMCP\docs\aux_files\
   Copy-Item C:\temp\maceira_postman_exampes.txt C:\CanaryMCP\docs\aux_files\
   ```

### 3.2 Configure environment variables
Create `C:\CanaryMCP\.env` with:
```
CANARY_SAF_BASE_URL=https://<canary-saf-host>
CANARY_VIEWS_BASE_URL=https://<canary-views-host>
CANARY_TIMEZONE=Europe/Lisbon
CANARY_MCP_TRANSPORT=http
CANARY_MCP_HOST=0.0.0.0
CANARY_MCP_PORT=6000
CANARY_TAG_METADATA_PATH=C:\CanaryMCP\docs\aux_files\Canary_Path_description_maceira.json
CANARY_TAG_NOTES_PATH=C:\CanaryMCP\docs\aux_files\maceira_postman_exampes.txt
```
Ensure `.env` is ACL-restricted (for example, grant read access only to `canarymcp` and Administrators).

### 3.3 Run as a Windows service
The two most common approaches:

1. **NSSM (Non-Sucking Service Manager)**  
   - Download NSSM from https://nssm.cc/download and place `nssm.exe` in `C:\Windows\System32`.
   - Register the service:
     ```powershell
     nssm install CanaryMCP "C:\CanaryMCP\.venv\Scripts\python.exe"
     nssm set CanaryMCP AppDirectory "C:\CanaryMCP"
     nssm set CanaryMCP AppParameters "-m canary_mcp.server"
     nssm set CanaryMCP AppEnvironmentExtra "PYTHONUNBUFFERED=1" "LOG_LEVEL=INFO"
     New-Item -ItemType Directory -Path "C:\CanaryMCP\logs" -Force | Out-Null
     nssm set CanaryMCP AppStdout "C:\CanaryMCP\logs\server.log"
     nssm set CanaryMCP AppStderr "C:\CanaryMCP\logs\server.err.log"
     nssm start CanaryMCP
     ```
     NSSM automatically restarts the process on failure. Make sure the logs directory exists and has write permission for the service account.

2. **Task Scheduler (fallback)**  
   - Create a scheduled task that runs `python -m canary_mcp.server` at startup, configured to run whether or not the user is logged on.  
   - Set the task to restart on failure and to run using the `canarymcp` account.

Whichever option you use, verify the service is reachable:
```powershell
Invoke-WebRequest http://localhost:6000/mcp/v1/health
```

### 3.4 Windows firewall and reverse proxy
- Allow inbound TCP 6000 (or the chosen port) in Windows Defender Firewall:
  ```powershell
  New-NetFirewallRule -DisplayName "Canary MCP HTTP" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 6000
  ```
- If the server is published externally, front it with IIS/ARR or an internal reverse proxy that terminates TLS and optionally enforces authentication (AD, mTLS, etc.).

---

## 4. Network & Reverse Proxy
1. **Firewall**: allow inbound traffic from the corporate network to TCP 6000 (or the proxy port).
2. **TLS termination** (recommended):
   - Configure Nginx/HAProxy on `vmhost8` (or edge gateway) to listen on `https://vmhost8.secil.pt/mcp` and forward to `http://127.0.0.1:6000`.
   - Enforce mTLS or token authentication if required.
3. **Health check**: once `CANARY_MCP_TRANSPORT=http`, FastMCP automatically serves `GET /mcp/v1/health`. Point monitoring at the reverse proxy endpoint.

## 6. Client Configuration (Claude Desktop)
1. **Update `claude_desktop_config.json`** for each user:
   ```json
   {
     "mcpServers": {
       "canary": {
         "type": "http",
         "url": "https://vmhost8.secil.pt/mcp",
         "headers": {
           "Authorization": "Bearer <enterprise-token-if-required>"
         }
       }
     }
   }
   ```
   - Replace the URL if a different proxy path is used.
   - Remove `headers` if the endpoint is already protected by network controls.

2. **Restart Claude Desktop** so it reloads the MCP configuration.

3. **Connection test**: inside Claude Desktop’s console, run the `get_server_info` tool. You should see the default timezone and aggregate list returned from the remote server.

## 7. Operational Checklist
- [ ] Reverse proxy and firewall rules deployed.
- [ ] systemd service running and enabled.
- [ ] Logs writing to `/var/log/canary-mcp/server.log` with log rotation (configure `logrotate` as needed).
- [ ] Secrets stored securely (Vault integration or restricted `.env`).
- [ ] Monitoring alarms for service outage, API error spikes, or authentication failures.
- [ ] Documentation distributed to client teams; sample configuration committed to `docs/`.

Following this runbook migrates the Canary MCP Server to an enterprise-accessible HTTP endpoint while preserving compliance with corporate security and operational guidelines.
