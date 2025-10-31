# Manual Installation Steps (Non-Admin User)

## 🔐 No Admin Rights Required!

All these steps work with regular user permissions.

---

## Step 1: Verify Your Files Exist

Check that these files exist in `C:\Github\BD\BD-hackaton-2025-10\`:
- ✅ `.env` (contains your Canary token)
- ✅ `claude_desktop_config.json` (Claude Desktop configuration)

---

## Step 2: Locate Your Claude Desktop Config Directory

Your Claude config directory should be at:
```
C:\Users\bsdias\AppData\Roaming\Claude\
```

**To get there quickly:**
1. Press `Win + R` (opens Run dialog)
2. Type: `%APPDATA%\Claude`
3. Press Enter

If the folder doesn't exist, create it:
1. Press `Win + R`
2. Type: `%APPDATA%`
3. Press Enter
4. Right-click → New → Folder → Name it "Claude"

---

## Step 3: Copy the Configuration File (Manual Method)

### Method A: Using File Explorer (Easiest)

1. **Open source folder:**
   - Navigate to: `C:\Github\BD\BD-hackaton-2025-10\`
   - Find: `claude_desktop_config.json`

2. **Copy the file:**
   - Right-click on `claude_desktop_config.json`
   - Click "Copy"

3. **Paste to Claude folder:**
   - Press `Win + R`
   - Type: `%APPDATA%\Claude`
   - Press Enter
   - Right-click in the empty space
   - Click "Paste"

**Result:** You should now have:
```
C:\Users\bsdias\AppData\Roaming\Claude\claude_desktop_config.json
```

### Method B: Using Command Prompt (Alternative)

1. Press `Win + R`
2. Type: `cmd`
3. Press Enter
4. Copy and paste this command:
   ```cmd
   copy "C:\Github\BD\BD-hackaton-2025-10\claude_desktop_config.json" "%APPDATA%\Claude\claude_desktop_config.json"
   ```
5. Press Enter

---

## Step 4: Verify Installation

Check that the file exists:
1. Press `Win + R`
2. Type: `%APPDATA%\Claude\claude_desktop_config.json`
3. Press Enter

The file should open in your default JSON/text editor showing:
```json
{
  "mcpServers": {
    "canary-historian": {
      ...
    }
  }
}
```

---

## Step 5: Restart Claude Desktop

1. **Close Claude Desktop completely:**
   - Look for Claude icon in system tray (bottom-right)
   - Right-click the icon
   - Click "Exit" or "Quit"
   - **OR** close all Claude windows and wait 10 seconds

2. **Restart Claude Desktop:**
   - Open Claude Desktop from Start Menu
   - Or from Desktop shortcut

---

## Step 6: Verify MCP Server Connection

Look for indicators that the MCP server is connected:
- 🔌 Plugin/MCP icon in Claude Desktop
- Server name "canary-historian" should appear
- Tool list should show available tools

If you don't see it immediately, try:
1. Opening the settings/preferences in Claude Desktop
2. Looking for "MCP Servers" or "Integrations" section
3. Verify "canary-historian" is listed and active

---

## Step 7: Test Basic Connectivity

In Claude Desktop, type:
```
Can you ping the Canary MCP server?
```

**Expected Response:**
```
pong - Canary MCP Server is running!
```

If this works, you're connected! 🎉

---

## 🔧 Troubleshooting (Non-Admin User)

### Issue: "Cannot run script" or "Execution policy"
**Solution:** Don't use PowerShell scripts. Use the manual copy method (Method A above).

### Issue: "Access denied" to Claude folder
**Cause:** The folder is in your user profile, so you should have access.
**Solution:**
1. Make sure you're using `%APPDATA%` not `%ProgramFiles%`
2. The correct path is: `C:\Users\bsdias\AppData\Roaming\Claude\`
3. This is YOUR user folder - no admin needed

### Issue: "uv: command not found" when testing
**Solution:** Make sure `uv` is installed in your user context:
```cmd
pip install --user uv
```

Or check if it's already installed:
```cmd
uv --version
```

### Issue: MCP server doesn't appear in Claude Desktop
**Possible causes:**
1. Config file not in the right location
2. JSON syntax error in config
3. Claude Desktop needs full restart (not just closing window)

**Solutions:**
1. Double-check file location: `%APPDATA%\Claude\claude_desktop_config.json`
2. Open the JSON file and verify no syntax errors
3. Use Task Manager to fully close Claude Desktop:
   - Press `Ctrl + Shift + Esc`
   - Find "Claude" processes
   - End all Claude tasks
   - Restart Claude Desktop

---

## 📋 Quick Verification Checklist

Before testing, verify:
- [ ] `.env` file exists in project folder with your token
- [ ] `claude_desktop_config.json` exists in `%APPDATA%\Claude\`
- [ ] Claude Desktop has been completely restarted
- [ ] You can see MCP server indicators in Claude Desktop

---

## 🎯 Ready to Test!

Once everything is set up, you can ask Claude:

**Test 1: Basic connectivity**
```
Ping the Canary MCP server
```

**Test 2: List hierarchy**
```
List the available namespaces in the Canary system
```

**Test 3: Your kiln query**
```
What is the latest value for kiln 5 431 shell velocity?
```

---

## 📝 Note About Story 1.10

There's a story planned (1.10: Non-admin user installation / Docker alternative) that will make this process even easier for non-admin users. For now, the manual copy method works perfectly!

---

**No admin rights needed - everything runs in your user context! 🚀**
