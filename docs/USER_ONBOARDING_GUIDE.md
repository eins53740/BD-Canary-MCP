# Canary MCP Server - User Onboarding Guide

**Version**: 1.0
**Date**: 2025-11-01
**Target Audience**: Engineers, Analysts, Plant Operations Staff
**Estimated Setup Time**: 15-30 minutes

---

## 📚 Table of Contents

1. [Welcome](#welcome)
2. [What is Canary MCP Server?](#what-is-canary-mcp-server)
3. [Prerequisites](#prerequisites)
4. [Installation Methods](#installation-methods)
5. [Step-by-Step Installation](#step-by-step-installation)
6. [First Time Setup](#first-time-setup)
7. [Your First Query](#your-first-query)
8. [Common Use Cases](#common-use-cases)
9. [Troubleshooting](#troubleshooting)
10. [Getting Help](#getting-help)

---

## 🎯 Welcome

Welcome to the Canary MCP Server! This guide will help you set up and start using natural language queries to access your plant's Canary Historian data through Claude Desktop.

### What You'll Learn
- ✅ How to install the MCP server on your PC
- ✅ How to connect it to Claude Desktop
- ✅ How to query Canary data using natural language
- ✅ Common query patterns for your daily work

---

## 🤔 What is Canary MCP Server?

The Canary MCP Server is a bridge between **Claude Desktop** (AI assistant) and your **Canary Historian** (plant data). It allows you to:

### Instead of This (Manual):
1. Open Canary Trend
2. Search for tag names
3. Configure time range
4. Export data
5. Analyze in Excel
6. Create charts manually

### You Can Do This (AI-Powered):
```
"Show me all temperature sensors for Kiln 6 from yesterday,
compare them to last week, and identify any anomalies"
```

**Result**: Claude analyzes the data, creates visualizations, and provides insights in seconds!

---

## 📖 Read This First: UNS/ISA‑95 Tag Guide

To help the AI understand plant structure and naming, the MCP server exposes a built‑in resource with our ISA‑95/UNS conventions for Maceira.

- Resource URI: `resource://canary/uns-tag-guide`
- Source file: `docs/aux_files/Maceira_UNS_Tag_Guide.md`

How to use:
- In Claude Desktop, say: “Read resource://canary/uns-tag-guide and keep it in working memory for translating natural language to Canary tag paths.”
- Claude can then use this context to resolve areas, equipment, and tag path patterns more accurately.

## ✅ Prerequisites

Before installing, ensure you have:

### Required
- [ ] **Windows 10 or 11** (64-bit)
- [ ] **Claude Desktop** installed ([Download here](https://claude.ai/download))
- [ ] **Internet access** (for installation only)
- [ ] **Canary API credentials** (provided by your IT department)

### Recommended
- [ ] **Basic knowledge of your plant's tag naming convention**
- [ ] **Understanding of your process areas** (e.g., Kiln 1, Mill 2, etc.)

### You DO NOT Need
- ❌ Administrator privileges (can install as regular user)
- ❌ Programming experience
- ❌ Database knowledge
- ❌ Previous MCP server experience

---

## 🚀 Installation Methods

Choose the method that works best for you:

### Method 1: Automated Script (Recommended) ⚡
**Best for**: Quick setup, minimal technical knowledge
**Time**: 10-15 minutes
**Difficulty**: ⭐ Easy

### Method 2: Manual Installation 🔧
**Best for**: Understanding each step, troubleshooting
**Time**: 20-30 minutes
**Difficulty**: ⭐⭐ Moderate

---

## 📥 Step-by-Step Installation

### Method 1: Automated Installation

#### Step 1: Download the Deployment Script

**Option A: From Email** (if IT sent it to you)
- Open the email from IT
- Download the `deploy_canary_mcp.ps1` file
- Save it to your **Downloads** folder

**Option B: From Network Share**
```
\\fileserver\IT\MCP-Deployments\deploy_canary_mcp.ps1
```

**Screenshot Placeholder**:
```
┌─────────────────────────────────────────┐
│ 📁 Downloads                             │
├─────────────────────────────────────────┤
│ deploy_canary_mcp.ps1         15 KB     │
│                                          │
│ [Right-click] → Run with PowerShell     │
└─────────────────────────────────────────┘
```

#### Step 2: Run the Script

1. **Right-click** on `deploy_canary_mcp.ps1`
2. Select **"Run with PowerShell"**

**Important**: If you see a security warning:
- Click **"More info"**
- Click **"Run anyway"**

**Screenshot Placeholder**:
```
┌─────────────────────────────────────────┐
│  Windows Protected your PC              │
│                                          │
│  [More info]                            │
│                                          │
│  Running: deploy_canary_mcp.ps1         │
└─────────────────────────────────────────┘
```

#### Step 3: Follow the Prompts

The script will ask you for:

**Prompt 1: Canary SAF URL**
```
Enter Canary SAF Base URL:
```
**Enter**: `https://scunscanary.secil.pt/api/v1`

**Prompt 2: Canary Views URL**
```
Enter Canary Views Base URL:
```
**Enter**: `https://scunscanary.secil.pt`

**Prompt 3: API Token**
```
Enter Canary API Token: (input hidden)
```
**Enter**: Your token (provided by IT - input will be hidden)

#### Step 4: Wait for Installation

The script will:
- ✓ Check prerequisites
- ✓ Install Python (if needed)
- ✓ Install uv package manager
- ✓ Download Canary MCP Server
- ✓ Configure everything automatically

**Screenshot Placeholder**:
```
╔════════════════════════════════════════════╗
║  Canary MCP Server Deployment v1.0         ║
╚════════════════════════════════════════════╝

[10:15:23] Checking prerequisites...
  [✓] PowerShell version: 5.1
  [✓] Sufficient disk space available
  [✓] Python version: 3.13.0
  [✓] Git is installed
  [✓] Internet connection verified

[10:15:45] Installing uv package manager...
  [✓] uv installed successfully

[10:16:12] Setting up repository...
  [✓] Repository cloned successfully
  [✓] Dependencies installed

[10:16:45] Creating environment configuration...
  [✓] Environment file created

[10:16:50] Configuring Claude Desktop...
  [✓] Claude Desktop configured successfully

╔════════════════════════════════════════════╗
║   Installation Completed Successfully!     ║
╚════════════════════════════════════════════╝
```

#### Step 5: Installation Complete! 🎉

You'll see a success message with next steps.

---

### Method 2: Manual Installation

<details>
<summary>Click to expand manual installation steps</summary>

#### Step 1: Install Python

1. Download Python 3.13 from https://www.python.org/downloads/
2. Run the installer
3. **Important**: Check "Add Python to PATH"
4. Click "Install Now"

#### Step 2: Install uv

Open PowerShell and run:
```powershell
irm https://astral.sh/uv/install.ps1 | iex
```

#### Step 3: Clone Repository

```powershell
cd $env:USERPROFILE\Documents
git clone https://github.com/your-org/BD-hackaton-2025-10.git
cd BD-hackaton-2025-10
```

#### Step 4: Install Dependencies

```powershell
uv sync
```

#### Step 5: Configure Environment

```powershell
copy .env.example .env
notepad .env
```

Edit the file with your credentials:
```
CANARY_SAF_BASE_URL=https://scunscanary.secil.pt/api/v1
CANARY_VIEWS_BASE_URL=https://scunscanary.secil.pt
CANARY_API_TOKEN=your-token-here
```

#### Step 6: Configure Claude Desktop

Edit `%APPDATA%\Claude\claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "canary-mcp-server": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\Users\\YourUsername\\Documents\\BD-hackaton-2025-10",
        "run",
        "python",
        "-m",
        "canary_mcp.server"
      ],
      "env": {
        "PYTHONPATH": "C:\\Users\\YourUsername\\Documents\\BD-hackaton-2025-10\\src"
      }
    }
  }
}
```

</details>

---

## 🎮 First Time Setup

### Step 1: Restart Claude Desktop

1. **Close Claude Desktop completely**
   - Look in the system tray (bottom-right corner)
   - Right-click the Claude icon
   - Click "Quit"

**Screenshot Placeholder**:
```
┌─────────────────────────────┐
│  ⬆ System Tray              │
├─────────────────────────────┤
│  🔊 Volume                   │
│  📶 Network                  │
│  🤖 Claude                   │
│     └─ [Quit]  ←── Click   │
└─────────────────────────────┘
```

2. **Start Claude Desktop again**
   - Open from Start Menu or Desktop shortcut

### Step 2: Verify Connection

Look for the **MCP indicator** in Claude Desktop:

**Screenshot Placeholder**:
```
┌─────────────────────────────────────────┐
│  Claude Desktop                    [x]  │
├─────────────────────────────────────────┤
│                                          │
│  🔌 MCP Servers: 1 Connected            │
│     canary-mcp-server ✓                 │
│                                          │
│  Chat window below...                   │
└─────────────────────────────────────────┘
```

### Step 3: Check Available Tools

In Claude Desktop, type:
```
What MCP tools are available?
```

**Expected Response**:
```
I can see the following Canary MCP Server tools:

1. ping - Test connection
2. list_namespaces - Browse Canary structure
3. search_tags - Find tags by pattern
4. get_tag_metadata - Get tag details
5. read_timeseries - Query historical data
6. get_server_info - Check Canary health
... (and more)
```

**✅ Success!** If you see this, you're ready to go!

**❌ No tools showing?** See [Troubleshooting](#troubleshooting)

---

## 🚦 Your First Query

Let's test the system with progressively more complex queries:

### Query 1: Connection Test
```
Can you ping the Canary server?
```

**Expected**: "pong! Canary MCP Server is running..."

**Screenshot Placeholder**:
```
┌──────────────────────────────────────────┐
│  You: Can you ping the Canary server?   │
├──────────────────────────────────────────┤
│  Claude:                                 │
│  I'll use the ping tool to test the      │
│  connection.                             │
│                                          │
│  🔧 Using tool: ping                     │
│  ✓ Result: pong! Canary MCP Server is    │
│            running. Version: 1.0.0       │
│                                          │
│  The server is connected and working!    │
└──────────────────────────────────────────┘
```

### Query 2: Explore Data Structure
```
What namespaces are available in our Canary system?
```

**Expected**: List of your plant areas (e.g., "Kiln 1", "Mill 2", etc.)

### Query 3: Search for Tags
```
Find all temperature sensors
```

**Expected**: List of temperature tags from your Canary system

### Query 4: Get Historical Data
```
Show me the last hour of data for Kiln 1 temperature
```

**Expected**: Data values with timestamps

**Screenshot Placeholder**:
```
┌──────────────────────────────────────────┐
│  You: Show me the last hour of data for │
│       Kiln 1 temperature                 │
├──────────────────────────────────────────┤
│  Claude:                                 │
│  I'll query the historical data.         │
│                                          │
│  🔧 Using tool: search_tags              │
│  Found: Kiln1.Temperature                │
│                                          │
│  🔧 Using tool: read_timeseries          │
│  Retrieved 60 data points                │
│                                          │
│  Here's the data:                        │
│  10:00 - 850.2°C                         │
│  10:01 - 851.1°C                         │
│  10:02 - 850.8°C                         │
│  ...                                     │
│                                          │
│  The temperature has been stable around  │
│  850°C for the past hour.                │
└──────────────────────────────────────────┘
```

---

## 💡 Common Use Cases

### Use Case 1: Daily Production Check
```
"Show me yesterday's key performance indicators for Kiln 6:
- Average temperature
- Production rate
- Fuel consumption
Create a summary report"
```

### Use Case 2: Troubleshooting
```
"Analyze the last 4 hours for Mill 2.
Look for any anomalies in vibration, temperature, or pressure.
What might have caused the alarm at 14:30?"
```

### Use Case 3: Shift Handover
```
"Generate a shift handover report for the last 8 hours covering:
- All alarms that occurred
- Equipment status changes
- Production statistics
- Notable events"
```

### Use Case 4: Trend Comparison
```
"Compare this week's cement mill energy consumption
to the same week last month.
What changed and why might consumption be different?"
```

### Use Case 5: Quality Validation
```
"Check if all kiln temperature sensors are reading
within normal ranges. Flag any that seem stuck or
out of spec."
```

**For More Examples**: See `docs/examples.md` in your installation folder

---

## 🔧 Troubleshooting

### Problem: "MCP Server Not Connected"

**Screenshot Placeholder**:
```
┌─────────────────────────────────────────┐
│  🔴 MCP Servers: 0 Connected            │
│     canary-mcp-server ✗ Not Connected   │
└─────────────────────────────────────────┘
```

**Solutions**:

1. **Check if Python is in PATH**
   - Open PowerShell
   - Type: `python --version`
   - Should show: `Python 3.11+`
   - If error: Reinstall Python with "Add to PATH" checked

2. **Verify Installation Path**
   - Open: `%APPDATA%\Claude\claude_desktop_config.json`
   - Check the `--directory` path matches where you installed
   - Update if needed

3. **Check Logs**
   - Open: `%APPDATA%\Claude\logs\`
   - Look for errors mentioning "canary-mcp-server"

4. **Restart Claude Desktop** (fully quit and reopen)

---

### Problem: "Authentication Failed"

**Error Message**: "Missing required credentials" or "Invalid API token"

**Solutions**:

1. **Verify .env file**
   - Open your installation folder
   - Check `.env` file exists
   - Verify credentials are correct (no extra spaces)

2. **Test credentials manually**
   - Open Canary Web UI
   - Try logging in with your credentials
   - If it fails, contact IT for new credentials

3. **Check URLs**
   - Ensure no trailing slashes in URLs
   - Correct: `https://scunscanary.secil.pt`
   - Wrong: `https://scunscanary.secil.pt/`

---

### Problem: "Query Returns No Data"

**Solutions**:

1. **Verify tag names**
   - Tag names are case-sensitive
   - Try: `"What tags are available?"` to browse

2. **Check time range**
   - Ensure querying a time when data exists
   - Try: `"from yesterday"` instead of specific times

3. **Network issues**
   - Verify you can access Canary Web UI
   - Check VPN if working remotely

---

### Problem: "Queries Are Slow"

**Solutions**:

1. **Reduce time range**
   - Instead of "last month", try "last week"
   - Canary API may have rate limits

2. **Cache warming**
   - First query is slower (building cache)
   - Subsequent similar queries will be faster

3. **Check network**
   - Test: `ping scunscanary.secil.pt`
   - Should be < 100ms

---

## 📞 Getting Help

### Quick Reference

| Issue | Solution |
|-------|----------|
| MCP not connected | Restart Claude Desktop |
| No tools showing | Check installation path in config |
| Authentication error | Verify .env credentials |
| Slow queries | Reduce time range, check network |
| Tag not found | Browse with `list_namespaces` first |

### Documentation

📁 **Your Installation Folder**: `Documents\Canary-MCP\`
- 📄 `docs/API.md` - Complete tool reference
- 📄 `docs/examples.md` - 20+ query examples
- 📄 `docs/DEPLOYMENT.md` - Advanced configuration
- 📄 `DEPLOYMENT_CHECKLIST.md` - Troubleshooting guide

### Support Contacts

**IT Helpdesk**: [Your IT contact]
**MCP Server Issues**: Check `docs/` folder first
**Canary API Issues**: Contact your Canary administrator

### Self-Help

1. **Check the examples**: `docs/examples.md`
2. **Run validation**:
   ```powershell
   cd Documents\Canary-MCP
   uv run python scripts/validate_installation.py
   ```
3. **Check logs**: `logs/canary-mcp-server.log`

---

## 🎓 Training Resources

### Video Tutorials (Coming Soon)
- [ ] Basic Installation
- [ ] Your First Query
- [ ] Advanced Query Patterns
- [ ] Troubleshooting Common Issues

### Workshops
- **New User Orientation** - Monthly
- **Advanced Query Techniques** - Quarterly
- **Power User Tips** - As requested

### Practice Queries

Start with these to build confidence:

```
1. "What tools can you use to access Canary data?"
2. "Show me all available namespaces"
3. "Find tags matching 'temperature'"
4. "Get the last hour of data for [your-favorite-tag]"
5. "Explain what the read_timeseries tool does"
```

---

## ✅ Onboarding Checklist

Track your progress:

### Installation
- [ ] Script downloaded
- [ ] Installation completed successfully
- [ ] Claude Desktop shows "Connected"

### First Tests
- [ ] Ping command worked
- [ ] Listed namespaces
- [ ] Searched for tags
- [ ] Retrieved time-series data

### Learning
- [ ] Read examples.md
- [ ] Tried 5+ different queries
- [ ] Understand error messages
- [ ] Know where to find help

### Daily Use
- [ ] Bookmarked common queries
- [ ] Integrated into daily workflow
- [ ] Sharing tips with colleagues
- [ ] Providing feedback to IT

---

## 🌟 Tips for Success

### DO:
✅ Start with simple queries and build complexity
✅ Use specific tag names when possible
✅ Specify clear time ranges
✅ Ask Claude to explain results
✅ Save useful query patterns

### DON'T:
❌ Query extremely long time ranges (> 1 month)
❌ Assume tag names (browse first)
❌ Ignore error messages (they're helpful!)
❌ Give up after one try (refine your query)
❌ Forget to check examples.md

---

## 📊 Success Metrics

You're successfully onboarded when you can:

1. ✅ Connect to Canary MCP Server without help
2. ✅ Query data for your daily work
3. ✅ Troubleshoot common issues yourself
4. ✅ Find and use relevant examples
5. ✅ Help onboard a colleague

**Average Time to Proficiency**: 1-2 weeks of regular use

---

## 🎉 Congratulations!

You're now ready to use the Canary MCP Server!

### Next Steps:
1. Try the practice queries above
2. Read through `docs/examples.md` for your use case
3. Start with simple daily queries
4. Gradually build more complex patterns
5. Share your success stories with the team!

### Feedback
We want to hear from you:
- What queries are most useful?
- What examples should we add?
- What could be easier?

**Contact**: [Your feedback channel]

---

**Guide Version**: 1.0
**Last Updated**: 2025-11-01
**Next Review**: 2025-12-01

Generated with [Claude Code](https://claude.com/claude-code)
