# Installation Troubleshooting Guide

This guide helps resolve common issues when installing the Canary MCP Server without administrator privileges on Windows.

## Common Issues and Solutions

### Issue 1: Python Not Found in PATH

**Symptoms:**
```
'python' is not recognized as an internal or external command
```

**Cause:** Python directory not added to user PATH environment variable

**Solution:**
1. Open "Edit environment variables for your account" (search in Start menu)
2. Under "User variables", select "Path" and click "Edit"
3. Verify this entry exists: `%USERPROFILE%\AppData\Local\Programs\Python313`
4. If missing, click "New" and add it
5. Click "OK" to save
6. **Restart your terminal** (close and reopen PowerShell/CMD)
7. Test: `python --version`

**Alternative:** Use full path to Python:
```powershell
%USERPROFILE%\AppData\Local\Programs\Python313\python.exe --version
```

---

### Issue 2: uv Command Not Found

**Symptoms:**
```
'uv' is not recognized as an internal or external command
```

**Cause:** uv binary not in PATH or not installed correctly

**Solution:**
1. Verify uv is installed:
   ```powershell
   dir %USERPROFILE%\.local\bin\uv.exe
   ```

2. If file doesn't exist, reinstall uv:
   ```powershell
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

3. Add uv to PATH:
   - Open "Edit environment variables for your account"
   - Under "User variables", select "Path" and click "Edit"
   - Add: `%USERPROFILE%\.local\bin`
   - Click "OK"

4. **Restart terminal** and test: `uv --version`

---

### Issue 3: Permission Errors During Installation

**Symptoms:**
```
PermissionError: [WinError 5] Access is denied
```

**Cause:** Trying to install to system directories instead of user directories

**Solution:**
1. **Verify installation location** is in your user profile:
   - Python: `%USERPROFILE%\AppData\Local\Programs\Python313`
   - uv: `%USERPROFILE%\.local\bin`

2. **Use uv pip** instead of pip (uv automatically installs to user space):
   ```powershell
   uv pip install -e .
   ```

3. **If pip is used**, add `--user` flag:
   ```powershell
   python -m pip install --user -e .
   ```

4. **Avoid these locations** (require admin):
   - `C:\Program Files\`
   - `C:\Python\`
   - System-wide package directories

---

### Issue 4: Network/Firewall Blocking Downloads

**Symptoms:**
```
ConnectionError: Failed to establish connection
TimeoutError: Connection timed out
```

**Cause:** Company firewall blocking Python package downloads or Canary API access

**Solution:**

**For Python/package downloads:**
1. **Check corporate proxy settings:**
   ```powershell
   # Set proxy for pip/uv
   set HTTP_PROXY=http://proxy.company.com:8080
   set HTTPS_PROXY=http://proxy.company.com:8080
   ```

2. **Configure uv to use proxy:**
   ```powershell
   uv pip install -e . --proxy http://proxy.company.com:8080
   ```

3. **Alternative: Download packages offline:**
   - Download wheels from https://pypi.org on a machine with internet
   - Transfer to your workstation
   - Install: `uv pip install package.whl`

**For Canary API access:**
1. **Verify Canary server URL** is accessible:
   ```powershell
   curl https://your-canary-server.com/health
   ```

2. **Contact IT** to whitelist:
   - Canary server domain/IP
   - Required ports (typically 443 for HTTPS)

3. **Check .env configuration:**
   - Verify `CANARY_SAF_BASE_URL` and `CANARY_VIEWS_BASE_URL` are correct
   - Try with/without trailing slashes
   - Verify API token is valid

---

### Issue 5: Missing Dependencies

**Symptoms:**
```
ModuleNotFoundError: No module named 'fastmcp'
ModuleNotFoundError: No module named 'httpx'
```

**Cause:** Dependencies not installed or installation incomplete

**Solution:**
1. **Reinstall dependencies:**
   ```powershell
   cd %USERPROFILE%\Documents\canary-mcp-server
   uv pip install -e .
   ```

2. **Verify dependencies installed:**
   ```powershell
   uv pip list
   ```
   Should show: fastmcp, httpx, python-dotenv, structlog

3. **Check Python version** (must be 3.13+):
   ```powershell
   python --version
   ```

4. **If dependencies still missing**, install individually:
   ```powershell
   uv pip install fastmcp httpx python-dotenv structlog
   ```

---

### Issue 6: Server Won't Start - Configuration Errors

**Symptoms:**
```
ConfigurationError: Missing required credentials: CANARY_API_TOKEN
CanaryAuthError: Authentication failed: Invalid API token
```

**Cause:** Missing or invalid .env configuration

**Solution:**
1. **Verify .env file exists:**
   ```powershell
   dir .env
   ```

2. **Check .env file location:**
   - Should be in project root or `%USERPROFILE%`
   - Server looks for `.env` in current directory first

3. **Validate .env contents:**
   ```ini
   # Required fields
   CANARY_SAF_BASE_URL=https://your-server.com/saf
   CANARY_VIEWS_BASE_URL=https://your-server.com/views
   CANARY_API_TOKEN=your-token-here
   ```

4. **Test API token manually:**
   ```powershell
   curl -X POST https://your-server.com/saf/getSessionToken `
     -H "Content-Type: application/json" `
     -d "{\"userToken\": \"your-token-here\"}"
   ```

5. **Get new API token** from Canary administrator if invalid

---

### Issue 7: Server Starts But Tools Don't Work

**Symptoms:**
- Server starts without errors
- MCP tool calls fail or timeout
- Logs show authentication or connection errors

**Cause:** Canary API connectivity or authentication issues

**Solution:**
1. **Check server logs:**
   ```powershell
   type logs\canary_mcp.log
   ```

2. **Look for specific errors:**
   - `CanaryAuthError`: Invalid credentials → Check API token
   - `ConnectError`: Can't reach server → Check firewall/network
   - `TimeoutException`: Slow connection → Increase timeout in .env

3. **Increase timeouts** if network is slow:
   ```ini
   # In .env file
   CANARY_REQUEST_TIMEOUT_SECONDS=30
   CANARY_SESSION_TIMEOUT_MS=300000
   ```

4. **Test Canary API directly:**
   - Use Postman or curl to test API endpoints
   - Verify namespaces exist: `/api/v2/browseNodes`
   - Verify tags searchable: `/api/v2/browseTags`

---

### Issue 8: Logs Directory Permission Denied

**Symptoms:**
```
PermissionError: [WinError 5] Access is denied: 'logs/canary_mcp.log'
```

**Cause:** Logs directory exists with restricted permissions

**Solution:**
1. **Delete existing logs directory:**
   ```powershell
   rmdir /s logs
   ```

2. **Restart server** - it will recreate the directory with user permissions

3. **Manually create with correct permissions:**
   ```powershell
   mkdir logs
   icacls logs /grant %USERNAME%:(OI)(CI)F
   ```

---

### Issue 9: Python Version Too Old

**Symptoms:**
```
Python 3.12.x found, but 3.13+ required
```

**Cause:** Older Python version installed

**Solution:**
1. **Verify Python version:**
   ```powershell
   python --version
   ```

2. **Download Python 3.13** from https://www.python.org/downloads/

3. **Install to user directory** (see Step 1 in installation guide)

4. **Update PATH** to use new Python:
   - Remove old Python path
   - Add new Python 3.13 path first in list

5. **Verify:**
   ```powershell
   python --version  # Should show 3.13.x
   ```

---

### Issue 10: Multiple Python Versions Conflict

**Symptoms:**
- Wrong Python version runs
- Packages installed but not found
- Import errors despite successful installation

**Cause:** Multiple Python installations, PATH pointing to wrong one

**Solution:**
1. **Check which Python is running:**
   ```powershell
   where python
   ```
   Shows all Python executables in PATH

2. **Use specific Python version:**
   ```powershell
   # Use full path to Python 3.13
   %USERPROFILE%\AppData\Local\Programs\Python313\python.exe -m canary_mcp.server
   ```

3. **Fix PATH order:**
   - Open "Edit environment variables for your account"
   - In "Path", move Python 3.13 directory to **top of list**
   - Remove or move other Python versions down

4. **Use virtual environment** to isolate:
   ```powershell
   python -m venv venv
   .\venv\Scripts\activate
   uv pip install -e .
   ```

---

## Still Having Issues?

### Collect Diagnostic Information

Run these commands and share output with support:

```powershell
# Python version and location
python --version
where python

# uv version and location
uv --version
where uv

# Installed packages
uv pip list

# Environment variables
echo %PATH%

# Canary MCP installation
python -c "import canary_mcp; print(canary_mcp.__file__)"

# Recent logs (last 50 lines)
powershell "Get-Content logs\canary_mcp.log -Tail 50"
```

### Contact Support

- **UNS Administrator:** Your internal Canary/UNS contact
- **GitHub Issues:** https://github.com/your-org/canary-mcp-server/issues
- **Documentation:** See [Installation Guide](./non-admin-windows.md)

---

## Prevention Tips

1. **Keep Python updated:** Check for Python 3.13.x updates monthly
2. **Backup .env file:** Store credentials securely (not in git)
3. **Document custom changes:** Note any company-specific configurations
4. **Test after updates:** Run validation script after any changes
5. **Monitor logs:** Check logs regularly for warnings or errors

---

**Last Updated:** 2025-10-31
