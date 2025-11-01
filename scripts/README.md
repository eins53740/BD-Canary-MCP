# Deployment Scripts - README

This directory contains automated deployment scripts for the Canary MCP Server.

## 📁 Files Overview

### For End Users

**`Install-Canary-MCP.cmd`** - Simple double-click installer
- **Purpose**: User-friendly wrapper for the PowerShell script
- **Usage**: Double-click to run
- **Best for**: Non-technical users
- **Time**: 15-30 minutes

### For IT Admins

**`deploy_canary_mcp.ps1`** - Full PowerShell deployment script
- **Purpose**: Automated installation with all checks
- **Usage**: Command-line or right-click → Run with PowerShell
- **Best for**: IT admins, scripted deployments
- **Time**: 10-15 minutes

**`validate_installation.py`** - Post-installation validation
- **Purpose**: Verify installation is working correctly
- **Usage**: `uv run python validate_installation.py`
- **Best for**: Troubleshooting, testing

**`benchmark.py`** - Performance testing
- **Purpose**: Measure query performance
- **Usage**: `uv run python benchmark.py --scenarios all`
- **Best for**: Performance validation

---

## 🚀 Quick Start

### For End Users

**Option 1: Simple Installer (Recommended)**
```cmd
1. Double-click: Install-Canary-MCP.cmd
2. Follow the prompts
3. Restart Claude Desktop
```

**Option 2: PowerShell Script**
```powershell
# Right-click deploy_canary_mcp.ps1 → Run with PowerShell
# OR run from PowerShell:
.\deploy_canary_mcp.ps1
```

---

### For IT Admins

#### Mass Deployment via Network Share

**Step 1: Set up shared deployment folder**
```
\\fileserver\IT\MCP-Deployments\
├── Install-Canary-MCP.cmd
├── deploy_canary_mcp.ps1
└── site-config.env  (pre-configured credentials)
```

**Step 2: Send email to users**
```
Subject: New Tool Available: Canary Data Assistant

Dear Team,

A new tool is available to query plant data using natural language.

Installation:
1. Open: \\fileserver\IT\MCP-Deployments\
2. Double-click: Install-Canary-MCP.cmd
3. Follow the prompts (15 minutes)
4. Restart Claude Desktop

Documentation: \\fileserver\IT\MCP-Deployments\docs\

Questions? Contact IT Helpdesk
```

#### Automated Deployment via Group Policy

**Step 1: Create deployment script**
```powershell
# deploy_via_gpo.ps1
$scriptUrl = "\\fileserver\IT\MCP-Deployments\deploy_canary_mcp.ps1"
$localScript = "$env:TEMP\deploy_canary_mcp.ps1"

Copy-Item $scriptUrl $localScript -Force

powershell -ExecutionPolicy Bypass -File $localScript `
    -CanarySafUrl "https://scunscanary.secil.pt/api/v1" `
    -CanaryViewsUrl "https://scunscanary.secil.pt" `
    -ApiToken "shared-readonly-token" `
    -SkipValidation
```

**Step 2: Deploy via GPO**
- Computer Configuration → Scripts → Startup
- Add: `deploy_via_gpo.ps1`
- Users get automatic installation on next login

#### Silent Installation (Unattended)

```powershell
.\deploy_canary_mcp.ps1 `
    -CanarySafUrl "https://scunscanary.secil.pt/api/v1" `
    -CanaryViewsUrl "https://scunscanary.secil.pt" `
    -ApiToken "your-token-here" `
    -InstallPath "C:\ProgramData\Canary-MCP" `
    -SkipValidation
```

---

## 🔧 Script Parameters

### deploy_canary_mcp.ps1

```powershell
-InstallPath <string>
    Installation directory
    Default: %USERPROFILE%\Documents\Canary-MCP

-CanarySafUrl <string>
    Canary SAF API base URL
    Example: https://scunscanary.secil.pt/api/v1

-CanaryViewsUrl <string>
    Canary Views base URL
    Example: https://scunscanary.secil.pt

-ApiToken <string>
    Canary API authentication token
    (Will prompt if not provided)

-SkipValidation <switch>
    Skip post-installation validation tests
    Use for faster silent installations
```

### Examples

**Interactive installation:**
```powershell
.\deploy_canary_mcp.ps1
```

**With credentials:**
```powershell
.\deploy_canary_mcp.ps1 `
    -CanarySafUrl "https://scunscanary.secil.pt/api/v1" `
    -CanaryViewsUrl "https://scunscanary.secil.pt" `
    -ApiToken "token-abc123"
```

**Custom location:**
```powershell
.\deploy_canary_mcp.ps1 `
    -InstallPath "D:\Tools\Canary-MCP"
```

**Silent mode:**
```powershell
.\deploy_canary_mcp.ps1 `
    -CanarySafUrl "..." `
    -CanaryViewsUrl "..." `
    -ApiToken "..." `
    -SkipValidation `
    -ErrorAction SilentlyContinue
```

---

## 📊 Deployment Strategies

### Strategy 1: Phased Rollout (Recommended)

**Week 1: Pilot Group (5-10 users)**
- Select tech-savvy early adopters
- Use interactive installation
- Collect feedback
- Refine documentation

**Week 2: Department (20-50 users)**
- Use shared network installation
- Provide training session
- IT support available

**Week 3-4: Company-wide (100+ users)**
- Automated GPO deployment
- Self-service portal
- Helpdesk prepared

### Strategy 2: Self-Service

**Setup**:
1. Place scripts on network share
2. Create documentation portal
3. Send announcement email
4. Users install themselves

**Pros**: Flexible, user-controlled
**Cons**: Requires user initiative

### Strategy 3: Centralized Deployment

**Setup**:
1. IT runs deployment script for each user
2. Schedule 1-on-1 sessions
3. Verify installation together

**Pros**: Guaranteed success, training included
**Cons**: Time-intensive for IT

---

## 🔍 Troubleshooting

### Script Won't Run

**Error**: "Running scripts is disabled on this system"

**Solution**:
```powershell
# Check current policy
Get-ExecutionPolicy

# If Restricted, run with bypass:
powershell -ExecutionPolicy Bypass -File .\deploy_canary_mcp.ps1
```

### Python Installation Fails

**Error**: "Failed to install Python"

**Solution**:
1. Download Python manually from python.org
2. Install with "Add to PATH" checked
3. Re-run deployment script (will skip Python installation)

### Git Not Found

**Error**: "Git is not installed"

**Solution**:
1. Install Git from https://git-scm.com/download/win
2. Or use portable Git for non-admin users
3. Re-run deployment script

### Network Issues

**Error**: "No internet connection"

**Solutions**:
- Check VPN connection
- Verify firewall allows github.com access
- Use offline installation method (see below)

---

## 💾 Offline Installation

For environments without internet access:

### Preparation (with internet):

```powershell
# 1. Download repository
git clone https://github.com/your-org/BD-hackaton-2025-10.git
cd BD-hackaton-2025-10

# 2. Download Python offline installer
# Download from: https://www.python.org/downloads/

# 3. Create deployment package
New-Item -ItemType Directory -Path "OfflineInstall" -Force
Copy-Item -Recurse * -Destination "OfflineInstall\"
# Copy Python installer to OfflineInstall\

# 4. Zip the folder
Compress-Archive -Path "OfflineInstall\*" -DestinationPath "Canary-MCP-Offline.zip"
```

### Installation (without internet):

```powershell
# 1. Extract deployment package
Expand-Archive "Canary-MCP-Offline.zip" -DestinationPath "C:\Temp\Canary-MCP"

# 2. Install Python
cd C:\Temp\Canary-MCP
.\python-3.13-installer.exe /quiet PrependPath=1

# 3. Install uv (requires brief internet access)
pip install uv

# 4. Run deployment
.\deploy_canary_mcp.ps1 -SkipValidation
```

---

## 📋 Pre-Deployment Checklist for IT

Before mass deployment, verify:

### Infrastructure
- [ ] Network share accessible by all users
- [ ] Firewall allows github.com (or use offline method)
- [ ] Canary API accessible from user PCs
- [ ] Adequate bandwidth for downloads (50MB per user)

### Credentials
- [ ] Canary API token generated
- [ ] Token tested and working
- [ ] Token has read-only permissions
- [ ] Token won't expire soon

### Support
- [ ] Helpdesk briefed on common issues
- [ ] Documentation distributed
- [ ] Training session scheduled (optional)
- [ ] Feedback channel established

### Testing
- [ ] Tested on representative user PC
- [ ] Tested with standard user account (not admin)
- [ ] Tested on Windows 10 and 11
- [ ] Tested with corporate antivirus
- [ ] Verified Claude Desktop compatibility

---

## 📞 Support

### For End Users
- **First**: Check USER_ONBOARDING_GUIDE.md
- **Second**: Run validation script
- **Third**: Contact IT helpdesk

### For IT Admins
- **Documentation**: docs/DEPLOYMENT.md
- **Logs**: Check PowerShell output
- **Validation**: Run `validate_installation.py`
- **Issues**: Check GitHub issues or contact vendor

---

## 🔄 Updates

### Update Existing Installations

```powershell
# Navigate to installation directory
cd $env:USERPROFILE\Documents\Canary-MCP

# Pull latest changes
git pull origin main

# Update dependencies
uv sync

# Restart Claude Desktop
```

### Automated Updates

Create scheduled task:
```powershell
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 2am
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-File C:\Scripts\update_canary_mcp.ps1"

Register-ScheduledTask -TaskName "Update Canary MCP" `
    -Trigger $trigger -Action $action `
    -Description "Weekly update of Canary MCP Server"
```

---

## 📊 Deployment Metrics

Track these metrics for successful rollout:

- **Installation success rate**: > 95%
- **Time to install**: < 30 minutes per user
- **Users active after 1 week**: > 80%
- **Support tickets**: < 5% of users
- **User satisfaction**: > 4/5 stars

---

## 🎯 Success Criteria

Deployment is successful when:

1. ✅ 90%+ of target users have installed
2. ✅ < 10% require helpdesk support
3. ✅ Users can complete basic queries independently
4. ✅ No critical issues reported
5. ✅ Positive feedback from users

---

**Scripts Version**: 1.0
**Last Updated**: 2025-11-01
**Maintained By**: IT Department

Generated with [Claude Code](https://claude.com/claude-code)
