# Debug MCP Server Startup Issues

## 🔍 Let's Find Out Why It Failed

---

## Step 1: Test Server Startup Manually

First, let's see if the server can start outside of Claude Desktop.

### Open Command Prompt and test:

```cmd
cd C:\Github\BD\BD-hackaton-2025-10
uv run python -m canary_mcp.server
```

**What to look for:**
- ✅ **Success**: "Starting Canary MCP Server on localhost:3000"
- ❌ **Error**: Any error messages about missing modules, imports, or configuration

**Press `Ctrl+C` to stop the server once you've seen the message.**

---

## Step 2: Check If `uv` Is in PATH

Claude Desktop might not find `uv` because it's not in the system PATH.

### Test if `uv` is accessible:

```cmd
uv --version
```

**If you get an error like "command not found":**
- `uv` is not in your PATH for Claude Desktop

**Solution options below in Step 3.**

---

## Step 3: Fix the PATH Issue

### Option A: Use Full Path to `uv` (Recommended)

Find where `uv` is installed:

```cmd
where uv
```

This will show something like:
```
C:\Users\bsdias\AppData\Local\Programs\uv\uv.exe
```

Then update your Claude Desktop config to use the full path:

```json
{
  "mcpServers": {
    "canary-historian": {
      "command": "C:\\Users\\bsdias\\AppData\\Local\\Programs\\uv\\uv.exe",
      "args": [
        "--directory",
        "C:/Github/BD/BD-hackaton-2025-10",
        "run",
        "python",
        "-m",
        "canary_mcp.server"
      ],
      "env": {
        "CANARY_SAF_BASE_URL": "https://scunscanary.secil.pt/api/v1",
        "CANARY_VIEWS_BASE_URL": "https://scunscanary.secil.pt",
        "CANARY_API_TOKEN": "0120fd2e-e9c2-4c8d-8115-a6ceb41490ce"
      }
    }
  }
}
```

**Note:** Use double backslashes `\\` in the path for Windows!

### Option B: Use Python Directly (Alternative)

If `uv` is causing issues, we can use Python directly:

First, activate your virtual environment and find the Python path:

```cmd
cd C:\Github\BD\BD-hackaton-2025-10
.venv\Scripts\activate
where python
```

Then use that Python path in the config:

```json
{
  "mcpServers": {
    "canary-historian": {
      "command": "C:\\Github\\BD\\BD-hackaton-2025-10\\.venv\\Scripts\\python.exe",
      "args": [
        "-m",
        "canary_mcp.server"
      ],
      "env": {
        "CANARY_SAF_BASE_URL": "https://scunscanary.secil.pt/api/v1",
        "CANARY_VIEWS_BASE_URL": "https://scunscanary.secil.pt",
        "CANARY_API_TOKEN": "0120fd2e-e9c2-4c8d-8115-a6ceb41490ce"
      }
    }
  }
}
```

---

## Step 4: Check Claude Desktop Logs

Claude Desktop logs can tell us exactly what went wrong.

### Windows Log Location:

```
%APPDATA%\Claude\logs\
```

Or full path:
```
C:\Users\bsdias\AppData\Roaming\Claude\logs\
```

### How to check logs:

1. Press `Win + R`
2. Type: `%APPDATA%\Claude\logs`
3. Press Enter
4. Look for recent log files (sorted by date)
5. Open the latest log file in Notepad
6. Search for "canary" or "error" or "failed"

**Look for error messages like:**
- "command not found: uv"
- "ModuleNotFoundError"
- "ImportError"
- "Connection refused"
- Any Python tracebacks

---

## Step 5: Check MCP Server Code for Startup Errors

Let's verify the server code doesn't have issues:

```cmd
cd C:\Github\BD\BD-hackaton-2025-10
uv run python -c "from canary_mcp.server import main; print('Import successful')"
```

**If this fails:**
- There's a problem with the code or dependencies
- Note the error message

**If this works:**
- The code is fine, it's a PATH/config issue

---

## Step 6: Test with Minimal Config

Create a test config to isolate the issue:

### Create: `test_config.json`

```json
{
  "mcpServers": {
    "canary-test": {
      "command": "python",
      "args": ["-c", "print('Hello from Python')"]
    }
  }
}
```

If this simple test fails, the issue is with how Claude Desktop runs commands.

---

## 🔧 Common Issues & Solutions

### Issue 1: "uv: command not found"
**Cause:** Claude Desktop can't find `uv` in PATH
**Solution:** Use full path to `uv.exe` (see Option A above)

### Issue 2: "ModuleNotFoundError: No module named 'canary_mcp'"
**Cause:** Dependencies not installed or wrong Python environment
**Solution:**
```cmd
cd C:\Github\BD\BD-hackaton-2025-10
uv sync --all-extras
```

### Issue 3: "ImportError: No module named 'fastmcp'"
**Cause:** FastMCP not installed
**Solution:**
```cmd
uv pip install fastmcp httpx python-dotenv
```

### Issue 4: Server starts but Claude can't connect
**Cause:** FastMCP needs to run in stdio mode for Claude Desktop
**Solution:** FastMCP should handle this automatically, but let's verify our server code.

### Issue 5: "Permission denied" or "Access denied"
**Cause:** File permissions issue
**Solution:** Make sure you have read/execute permissions on the project folder

---

## 🧪 Quick Diagnostic Script

Run this to check everything:

```cmd
@echo off
echo ====================================
echo MCP Server Diagnostic
echo ====================================
echo.

echo 1. Checking if uv is installed...
where uv
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: uv not found in PATH!
) else (
    echo OK: uv found
)
echo.

echo 2. Checking Python in virtual environment...
cd C:\Github\BD\BD-hackaton-2025-10
if exist .venv\Scripts\python.exe (
    echo OK: Virtual environment exists
    .venv\Scripts\python.exe --version
) else (
    echo ERROR: Virtual environment not found!
)
echo.

echo 3. Checking if canary_mcp module can be imported...
.venv\Scripts\python.exe -c "import canary_mcp; print('OK: Module imports successfully')"
echo.

echo 4. Testing server startup (will start for 3 seconds)...
start /B .venv\Scripts\python.exe -m canary_mcp.server
timeout /t 3 /nobreak > nul
taskkill /F /IM python.exe /T > nul 2>&1
echo.

echo ====================================
echo Diagnostic complete!
echo ====================================
pause
```

Save this as `diagnose.bat` and run it.

---

## ✅ Verification Steps After Fix

Once you've applied a fix:

1. **Restart Claude Desktop completely**
   - Close all windows
   - Wait 10 seconds
   - Reopen Claude Desktop

2. **Check for the MCP indicator**
   - Look for "canary-historian" in the MCP servers list
   - Should show as "Connected" or "Active"

3. **Test basic command:**
   ```
   Can you ping the Canary MCP server?
   ```

4. **If still failing:**
   - Check Claude Desktop logs again
   - Try the simpler Python direct path method
   - Share the error message for more help

---

## 📞 Need More Help?

If none of these work, share:
1. The output of `where uv`
2. The output of `uv run python -m canary_mcp.server`
3. The latest error from Claude Desktop logs
4. Any error messages you see

---

**Most likely fix: Use the full path to `uv.exe` in the config!**
