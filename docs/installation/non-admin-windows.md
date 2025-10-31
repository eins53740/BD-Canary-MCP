# Non-Admin Windows Installation Guide

This guide explains how to install and run the Canary MCP Server on Windows **without administrator privileges**. This is ideal for company workstations where you don't have IT admin access.

## Prerequisites

- Windows 10 or Windows 11
- No administrator privileges required
- Internet connection for downloading Python and dependencies

## Installation Steps

### Step 1: Install Python 3.13 Portable (No Admin Required)

1. **Download Python 3.13 embeddable package:**
   - Visit https://www.python.org/downloads/windows/
   - Scroll to "Windows embeddable package (64-bit)" for Python 3.13.x
   - Download the `.zip` file (e.g., `python-3.13.0-embed-amd64.zip`)

2. **Extract Python to your user directory:**
   ```
   # Extract to a location in your user profile (no admin needed)
   %USERPROFILE%\AppData\Local\Programs\Python313
   ```
   - Create the directory if it doesn't exist
   - Extract the entire contents of the zip file

3. **Add Python to your user PATH:**
   - Open "Edit environment variables for your account" (search in Start menu)
   - Under "User variables", select "Path" and click "Edit"
   - Click "New" and add: `%USERPROFILE%\AppData\Local\Programs\Python313`
   - Click "OK" to save

4. **Verify Python installation:**
   ```powershell
   python --version
   ```
   You should see: `Python 3.13.x`

### Step 2: Install uv Package Manager (No Admin Required)

1. **Download and install uv to user directory:**
   ```powershell
   # Create local bin directory for user executables
   mkdir %USERPROFILE%\.local\bin

   # Download uv installer
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

   The installer will automatically place uv in `%USERPROFILE%\.local\bin`

2. **Add uv to your user PATH:**
   - Open "Edit environment variables for your account"
   - Under "User variables", select "Path" and click "Edit"
   - Click "New" and add: `%USERPROFILE%\.local\bin`
   - Click "OK" to save

3. **Restart your terminal** (close and reopen PowerShell or Command Prompt)

4. **Verify uv installation:**
   ```powershell
   uv --version
   ```
   You should see the uv version number

### Step 3: Install Canary MCP Server (User-Space)

1. **Clone or download the Canary MCP Server repository:**
   ```powershell
   cd %USERPROFILE%\Documents
   git clone https://github.com/your-org/canary-mcp-server.git
   cd canary-mcp-server
   ```

   Or download the ZIP from GitHub and extract it

2. **Install the MCP server and dependencies:**
   ```powershell
   # Install to user directory (no admin required)
   uv pip install -e .
   ```

   This installs all dependencies from `pyproject.toml` to your user Python environment

3. **Verify installation:**
   ```powershell
   python -m canary_mcp.server --help
   ```
   You should see the server help message

### Step 4: Configure Environment Variables

1. **Create a `.env` file** in your user home directory or project directory:
   ```powershell
   cd %USERPROFILE%\Documents\canary-mcp-server
   copy .env.example .env
   notepad .env
   ```

2. **Edit the `.env` file** with your Canary API credentials:
   ```ini
   # Canary API Configuration
   CANARY_SAF_BASE_URL=https://your-canary-server.com/saf
   CANARY_VIEWS_BASE_URL=https://your-canary-server.com/views
   CANARY_API_TOKEN=your-api-token-here

   # Optional: Logging Configuration
   LOG_LEVEL=INFO

   # Optional: Session and Request Timeouts
   CANARY_SESSION_TIMEOUT_MS=120000
   CANARY_REQUEST_TIMEOUT_SECONDS=10
   CANARY_RETRY_ATTEMPTS=3
   ```

3. **Save and close** the file

### Step 5: Validate Installation

Run the installation validation script to confirm everything is set up correctly:

```powershell
python scripts/validate_installation.py
```

The script will check:
- ✅ Python version >= 3.13
- ✅ uv is installed and in PATH
- ✅ Canary MCP Server package installed
- ✅ Configuration file exists and is valid
- ✅ Server can start without admin privileges

If all checks pass, you're ready to run the MCP server!

### Step 6: Start the MCP Server

Start the server as a regular user process (no admin required):

```powershell
python -m canary_mcp.server
```

The server will:
- Load configuration from `.env` file
- Authenticate with Canary API
- Start listening for MCP tool calls
- Create logs in `logs/` directory (auto-created, no admin needed)

**Keep the terminal window open** while the server is running.

## Verification

Test the server is working:

1. **Check server health:**
   ```powershell
   # In another terminal
   curl http://localhost:8000/health
   ```

2. **View logs:**
   ```powershell
   type logs\canary_mcp.log
   ```

## Next Steps

- **Connect Claude Desktop:** Configure Claude to use this MCP server
- **Test MCP tools:** Try `list_namespaces`, `search_tags`, `read_timeseries`
- **Monitor logs:** Check `logs/canary_mcp.log` for any issues

## Troubleshooting

If you encounter issues, see [Troubleshooting Guide](./troubleshooting.md) for common problems and solutions.

## Security Notes

- **No admin privileges required:** All installation and execution happens in user space
- **Credentials security:** Keep your `.env` file secure (never commit to source control)
- **Network access:** Ensure your company firewall allows connections to Canary server
- **Log access:** Logs are written to user-accessible directory only

## Uninstallation

To remove the Canary MCP Server:

1. **Uninstall Python package:**
   ```powershell
   uv pip uninstall canary-mcp-server
   ```

2. **Remove installation directory:**
   ```powershell
   rmdir /s %USERPROFILE%\Documents\canary-mcp-server
   ```

3. **Optional: Remove Python and uv** (if not needed for other projects):
   - Remove Python directory: `%USERPROFILE%\AppData\Local\Programs\Python313`
   - Remove uv directory: `%USERPROFILE%\.local\bin`
   - Remove PATH entries added in Step 1 and Step 2

---

**Need help?** See [Troubleshooting Guide](./troubleshooting.md) or contact your UNS administrator.
