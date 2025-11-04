# Claude Desktop MCP Server Setup

This guide explains how to configure Claude Desktop to use your Canary MCP Server.

## Prerequisites

- Claude Desktop installed
- Canary MCP Server set up (Epic 01 complete)
- `.env` file configured with Canary API credentials

## Step 1: Locate Claude Desktop Configuration

The configuration file is located at:
```
%APPDATA%\Claude\claude_desktop_config.json
```

Full path typically:
```
C:\Users\<YourUsername>\AppData\Roaming\Claude\claude_desktop_config.json
```

## Step 2: Create/Edit Configuration File

**If the file doesn't exist**, create it with the following content:

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

**If the file exists**, add the `canary-mcp-server` entry to the existing `mcpServers` object.

## Step 3: Update Paths

Replace `C:\\Github\\BD\\BD-hackaton-2025-10` with your actual project path.

**Important:** Use double backslashes (`\\`) in the JSON file for Windows paths.

## Step 4: Alternative Configuration (Using Python Directly)

If you prefer to use Python directly without uv:

```json
{
  "mcpServers": {
    "canary-mcp-server": {
      "command": "C:\\Github\\BD\\BD-hackaton-2025-10\\.venv\\Scripts\\python.exe",
      "args": [
        "-m",
        "canary_mcp.server"
      ],
      "env": {
        "PYTHONPATH": "C:\\Github\\BD\\BD-hackaton-2025-10\\src",
        "CANARY_SAF_BASE_URL": "https://scunscanary.secil.pt/api/v1",
        "CANARY_VIEWS_BASE_URL": "https://scunscanary.secil.pt",
        "CANARY_API_TOKEN": "your-api-token-here",
        "CANARY_TAG_SEARCH_ROOT": "Secil.Portugal",
        "CANARY_TAG_SEARCH_FALLBACKS": "Secil.Portugal"
      }
    }
  }
}
```

**Note:** If you include credentials in the config, make sure the file permissions are secure.

## Step 5: Restart Claude Desktop

1. **Close Claude Desktop completely** (check system tray)
2. **Restart Claude Desktop**
3. The MCP server should now be available

## Step 6: Verify MCP Server Connection

In Claude Desktop, you should see:
- MCP server indicator in the interface (usually bottom-left or settings)
- "canary-mcp-server" listed as connected
- Available tools listed

## Step 7: Test MCP Tools

Try these commands in Claude Desktop:

### Test 1: Get Server Info
```
Use the get_server_info tool to check the Canary server connection
```

### Test 2: List Namespaces
```
Use the list_namespaces tool to show me the available Canary namespaces
```

### Test 3: Search Tags
```
Use the search_tags tool to find tags matching the pattern "Temperature*"
```

### Test 4: Read Timeseries Data
```
Use the read_timeseries tool to get data for tag "Secil.Line1.Temperature"
from yesterday to now
```

## Troubleshooting

### Issue 1: MCP Server Not Appearing

**Check:**
- Claude Desktop version supports MCP (version 0.7.0+)
- Configuration file syntax is valid JSON
- Paths use double backslashes (`\\`)
- Claude Desktop was fully restarted

**Solution:**
```bash
# Validate JSON syntax
type "%APPDATA%\Claude\claude_desktop_config.json"

# Check Claude Desktop logs
# Location: %APPDATA%\Claude\logs
```

### Issue 2: Server Connects but Tools Don't Work

**Check:**
- `.env` file exists in project root
- Canary API credentials are correct
- Server can reach Canary instance

**Solution:**
```bash
# Test server manually
cd C:\Github\BD\BD-hackaton-2025-10
uv run python -m canary_mcp.server

# Validate environment
python scripts/validate_installation.py
```

### Issue 3: Authentication Errors

**Check:**
- `CANARY_API_TOKEN` is valid and not expired
- `CANARY_SAF_BASE_URL` and `CANARY_VIEWS_BASE_URL` are correct
- Network allows access to Canary server

**Solution:**
```bash
# Test API connection
curl https://scunscanary.secil.pt/api/v1/

# Verify credentials in .env
type .env
```

### Issue 4: Path Issues on Windows

**Common mistakes:**
- Single backslash instead of double (`\` vs `\\`)
- Forward slashes in Windows paths (`/` instead of `\\`)
- Spaces in paths not properly escaped

**Solution:**
```json
// Correct ✅
"C:\\Github\\BD\\BD-hackaton-2025-10"

// Wrong ❌
"C:\Github\BD\BD-hackaton-2025-10"
"C:/Github/BD/BD-hackaton-2025-10"
```

### Issue 5: Server Crashes on Startup

**Check logs:**
```bash
# Claude Desktop logs
dir "%APPDATA%\Claude\logs"

# Check server can start manually
cd C:\Github\BD\BD-hackaton-2025-10
uv run python -m canary_mcp.server
```

## Configuration Examples

### Example 1: Basic Configuration
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
      ]
    }
  }
}
```

### Example 2: With Environment Variables
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
        "PYTHONPATH": "C:\\Github\\BD\\BD-hackaton-2025-10\\src",
        "LOG_LEVEL": "DEBUG"
      }
    }
  }
}
```

### Example 3: Multiple MCP Servers
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
      ]
    },
    "other-mcp-server": {
      "command": "node",
      "args": [
        "C:\\path\\to\\other-server\\index.js"
      ]
    }
  }
}
```

## Verifying the Setup

### Check 1: Configuration File Syntax
```bash
# Use Python to validate JSON
python -m json.tool "%APPDATA%\Claude\claude_desktop_config.json"
```

### Check 2: Server Can Start
```bash
cd C:\Github\BD\BD-hackaton-2025-10
uv run python -m canary_mcp.server
# Should start without errors (Ctrl+C to stop)
```

### Check 3: Dependencies Installed
```bash
cd C:\Github\BD\BD-hackaton-2025-10
python scripts/validate_installation.py
# Should show all checks passing
```

### Check 4: Claude Desktop Version
- Open Claude Desktop
- Go to Settings → About
- Verify version is 0.7.0 or higher (MCP support)

## Expected Behavior

When properly configured:

1. **Startup:**
   - Claude Desktop starts normally
   - MCP server indicator shows "Connected" or green status
   - "canary-mcp-server" appears in MCP servers list

2. **Tool Usage:**
   - You can ask Claude to use any of the 5 tools
   - Tools appear in autocomplete/suggestions
   - Tool results display in the conversation

3. **Available Tools:**
   - `ping` - Test MCP server connection
   - `list_namespaces` - Browse Canary hierarchical structure
   - `search_tags` - Find tags by pattern
   - `get_tag_metadata` - Get detailed tag information
   - `read_timeseries` - Query historical data
   - `get_server_info` - Check Canary server health

## Next Steps

After successful setup:

1. Test all MCP tools with sample queries
2. Explore your Canary data using natural language
3. Create custom workflows combining multiple tools
4. Share useful query patterns with your team

## Additional Resources

- [MCP Protocol Documentation](https://modelcontextprotocol.io/)
- [Claude Desktop MCP Guide](https://docs.anthropic.com/claude/docs/mcp)
- [Canary MCP Server README](../../README.md)
- [Troubleshooting Guide](troubleshooting.md)

---

**Setup Time:** ~5 minutes
**Difficulty:** Easy
**Prerequisites:** Claude Desktop 0.7.0+, Canary MCP Server installed
