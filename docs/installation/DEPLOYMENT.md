# Canary MCP Server Deployment Guide

**Story 2.8: Deployment Guide & Site Rollout Documentation**

This guide provides step-by-step instructions for deploying the Canary MCP Server to production sites. Follow these procedures to ensure consistent, reliable deployments.

---

## Table of Contents

1. [Deployment Overview](#deployment-overview)
2. [Pre-Deployment Checklist](#pre-deployment-checklist)
3. [Installation Steps](#installation-steps)
4. [Configuration Setup](#configuration-setup)
5. [Connection Validation](#connection-validation)
6. [Performance Verification](#performance-verification)
7. [User Onboarding](#user-onboarding)
8. [Troubleshooting](#troubleshooting)
9. [Rollback Procedures](#rollback-procedures)
10. [Post-Deployment Monitoring](#post-deployment-monitoring)

---

## Deployment Overview

### Deployment Timeline

**Estimated time per site: 20-30 minutes**

- Pre-deployment checks: 5 minutes
- Installation: 10 minutes
- Configuration & validation: 5-10 minutes
- Performance verification: 5 minutes
- User onboarding: Variable (can be done separately)

### Deployment Paths

The MCP server supports two deployment methods:

| Method | Use Case | Time | Requirements |
|--------|----------|------|--------------|
| **Non-Admin Windows** | Standard workstations | 10-15 min | Python 3.11+, `uv` package manager |
| **Docker** | Production servers | 5-10 min | Docker Desktop with admin rights |

**Recommendation:** Use **Non-Admin Windows** for single-site deployment as specified in project requirements.

---

## Pre-Deployment Checklist

Complete this checklist **before** starting installation:

### 1. Environment Requirements

- [ ] **Windows 10/11** (64-bit)
- [ ] **Python 3.11 or higher** installed
- [ ] **`uv` package manager** installed (`pip install uv`)
- [ ] **Network access** to Canary Views API
- [ ] **Claude Desktop** installed (if using Claude)
- [ ] **Git** installed (for cloning repository)

### 2. Canary API Credentials

Obtain from your Canary administrator:

- [ ] **Canary SAF Base URL** (`CANARY_SAF_BASE_URL`)
- [ ] **Canary Views Base URL** (`CANARY_VIEWS_BASE_URL`)
- [ ] **API Token** (`CANARY_API_TOKEN`)
- [ ] **Test credentials** with read-only access

**Verification:** Test credentials manually using Canary Views Web UI before deployment.

### 3. Site Information

- [ ] **Site name/identifier**
- [ ] **Canary instance details** (version, timezone)
- [ ] **Expected tag count** (for performance planning)
- [ ] **Primary use cases** (for user onboarding)
- [ ] **Point of contact** for site-specific questions

### 4. Infrastructure Readiness

- [ ] **Disk space**: Minimum 500MB free (1GB recommended for cache)
- [ ] **Memory**: Minimum 2GB available RAM
- [ ] **Network**: <100ms latency to Canary API (test with `ping`)
- [ ] **Firewall**: Ports opened if required (typically not needed for outbound HTTPS)

---

## Installation Steps

### Step 1: Clone Repository

```bash
cd C:\Github\BD
git clone https://github.com/your-org/BD-hackaton-2025-10.git
cd BD-hackaton-2025-10
```

**Verification:** Confirm `src/canary_mcp/server.py` exists.

### Step 2: Install Dependencies

```bash
# Install dependencies using uv
uv sync

# Verify installation
uv run python -c "import canary_mcp; print('Installation successful')"
```

**Expected output:** `Installation successful`

**Troubleshooting:** If `uv` not found, run `pip install uv` first.

### Step 3: Run Installation Validation

```bash
# Run automated validation script
uv run python scripts/validate_installation.py
```

**Expected output:** All checks should pass (green checkmarks).

---

## Configuration Setup

### Step 1: Create `.env` File

Copy the example configuration:

```bash
copy .env.example .env
```

### Step 2: Configure Canary API Credentials

Edit `.env` with your site-specific values:

```bash
# Canary API Configuration (REQUIRED)
CANARY_SAF_BASE_URL=https://your-canary-saf.example.com/api/v1
CANARY_VIEWS_BASE_URL=https://your-canary-views.example.com
CANARY_API_TOKEN=your-api-token-here

# Session Configuration
CANARY_SESSION_TIMEOUT_MS=120000

# Performance Settings (Story 2.1)
CANARY_POOL_SIZE=10
CANARY_TIMEOUT=30
CANARY_RETRY_ATTEMPTS=3

# Cache Configuration (Story 2.2)
CANARY_CACHE_DIR=.cache
CANARY_CACHE_METADATA_TTL=3600
CANARY_CACHE_TIMESERIES_TTL=300
CANARY_CACHE_MAX_SIZE_MB=100

# Circuit Breaker (Story 2.3)
CANARY_CIRCUIT_CONSECUTIVE_FAILURES=5
CANARY_CIRCUIT_RESET_SECONDS=60

# Logging
LOG_LEVEL=INFO
```

### Step 3: Validate Configuration

```bash
# Test API connectivity
uv run python -c "from canary_mcp.auth import CanaryAuthClient; import asyncio; asyncio.run(CanaryAuthClient().authenticate()); print('Connection successful')"
```

**Expected output:** `Connection successful`

**If failed:**
- Verify URLs are correct (no trailing slashes)
- Check API token validity
- Confirm network connectivity

---

## Connection Validation

### MCP Inspector (Interactive Test)

Use the MCP Inspector to validate the server interactively from this directory:

```bash
npx @modelcontextprotocol/inspector uv --directory . run canary-mcp
```

This opens the Inspector UI in your browser and starts the server via uv.

### Test 1: Ping Tool

```bash
uv run python -c "from canary_mcp.server import ping; print(ping())"
```

**Expected:** `pong! Canary MCP Server is running. Version: 1.0.0`

### Test 2: Authentication

```bash
# Test script included in repository
uv run python test_canary_connection.py
```

**Expected:** Connection successful with session token displayed.

### Test 3: List Namespaces

```bash
uv run python -c "from canary_mcp.server import list_namespaces; import asyncio; result = asyncio.run(list_namespaces()); print(f'Found {result[\"count\"]} namespaces')"
```

**Expected:** Count of namespaces from your Canary instance.

### Test 4: Search Tags

```bash
# Search for a known tag (replace with site-specific tag)
uv run python -c "from canary_mcp.server import search_tags; import asyncio; result = asyncio.run(search_tags('Temperature')); print(f'Found {result[\"count\"]} tags')"
```

**Expected:** List of matching tags.

---

## Performance Verification

### Run Performance Baseline

```bash
# Run benchmark tool (Story 2.1)
uv run python scripts/benchmark.py --scenarios all
```

**Expected results:**
- ✅ Single query: Median < 5s
- ✅ 10 concurrent: Median < 5s, 95%+ success
- ✅ 25 concurrent: Median < 6s, 95%+ success

**If performance is poor:**
- Check `CANARY_POOL_SIZE` (increase to 25 for high concurrency)
- Verify network latency to Canary API (`ping <canary-url>`)
- Check cache configuration (`CANARY_CACHE_MAX_SIZE_MB`)

### Run Integration Tests

```bash
# Run performance validation suite (Story 2.4)
uv run pytest tests/integration/test_performance_suite.py -v
```

**Expected:** All 7 tests pass.

### Health Check

```bash
# Verify system health
uv run python -c "from canary_mcp.server import get_health; import json; print(json.dumps(get_health(), indent=2))"
```

**Expected output:**
```json
{
  "status": "healthy",
  "circuit_breakers": {
    "canary-api": {
      "state": "closed"
    }
  },
  "cache_health": {
    "operational": true
  }
}
```

---

## User Onboarding

### For Claude Desktop Users

#### Step 1: Configure Claude Desktop

1. Open Claude Desktop configuration file:
   ```
   %APPDATA%\Claude\claude_desktop_config.json
   ```

2. Add Canary MCP Server:
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

3. Restart Claude Desktop

**Verification:** Open Claude Desktop and type: "What MCP tools are available?"

#### Step 2: Test Basic Queries

Try these example queries:

1. **Check connection:**
   ```
   "Can you ping the Canary server?"
   ```

2. **List data sources:**
   ```
   "What namespaces are available in Canary?"
   ```

3. **Search for tags:**
   ```
   "Find all temperature sensors"
   ```

4. **Get recent data:**
   ```
   "Show me the last 10 minutes of data for [specific tag]"
   ```

#### Step 3: Share Example Library

Provide users with the example query library:
- **Location:** `docs/examples.md`
- **Contents:** 20+ real-world examples organized by use case

---

## Troubleshooting

### Common Issues

#### Issue: "Module not found: canary_mcp"

**Cause:** PYTHONPATH not set correctly.

**Solution:**
```bash
# Set PYTHONPATH in .env
PYTHONPATH=C:\Github\BD\BD-hackaton-2025-10\src
```

#### Issue: "Authentication failed"

**Causes:**
- Invalid API token
- Expired token
- Incorrect URLs

**Solutions:**
1. Verify token in Canary Web UI
2. Check URLs have no trailing slashes
3. Test manually: `curl <SAF_URL>/getSessionToken`

#### Issue: "Connection timeout"

**Causes:**
- Network latency
- Firewall blocking
- Canary server down

**Solutions:**
1. Check network: `ping <canary-host>`
2. Increase timeout: `CANARY_TIMEOUT=60`
3. Contact Canary administrator

#### Issue: "Circuit breaker open"

**Cause:** Too many consecutive failures.

**Solution:**
1. Check health: `get_health()` tool
2. Wait 60 seconds for auto-recovery
3. Check Canary API status
4. Review logs: `logs/canary-mcp-server.log`

#### Issue: "Slow query performance"

**Solutions:**
1. Check cache hit rate: `get_cache_stats()` tool
2. Increase cache size: `CANARY_CACHE_MAX_SIZE_MB=200`
3. Increase connection pool: `CANARY_POOL_SIZE=25`
4. Verify network latency

### Log Analysis

**Log location:** `logs/canary-mcp-server.log`

**Key log patterns:**
- `authentication_success` - API token valid
- `cache_hit` - Query served from cache
- `circuit_breaker_opened` - Too many failures
- `retry_attempt` - Transient error recovery

---

## Rollback Procedures

### When to Rollback

- Critical functionality broken
- Performance degraded significantly
- Security issue discovered
- User-reported data accuracy problems

### Rollback Steps

#### Option 1: Revert to Previous Version

```bash
# Navigate to repository
cd C:\Github\BD\BD-hackaton-2025-10

# Check current branch
git branch

# Revert to previous commit
git log --oneline  # Find last working commit
git checkout <commit-hash>

# Reinstall dependencies
uv sync

# Restart server
```

#### Option 2: Restore Configuration

```bash
# Restore previous .env file
copy .env.backup .env

# Verify configuration
uv run python scripts/validate_installation.py
```

#### Option 3: Complete Removal

```bash
# Stop MCP server (close Claude Desktop)

# Remove installation
cd C:\Github\BD
rmdir /s /q BD-hackaton-2025-10

# Remove Claude Desktop config
# Edit: %APPDATA%\Claude\claude_desktop_config.json
# Remove "canary-mcp-server" entry
```

---

## Post-Deployment Monitoring

### Daily Checks (Automated)

Set up automated monitoring:

```bash
# Schedule daily health check (Windows Task Scheduler)
# Task: Run at 8 AM daily
# Action: uv run python -c "from canary_mcp.server import get_health; result = get_health(); exit(0 if result['status'] == 'healthy' else 1)"
```

### Weekly Review

Review these metrics weekly:

1. **Performance Metrics:**
   ```bash
   uv run python -c "from canary_mcp.server import get_metrics_summary; import json; print(json.dumps(get_metrics_summary(), indent=2))"
   ```

   **Key metrics:**
   - Average query latency
   - Cache hit rate (target: >70%)
   - Error rate (target: <5%)

2. **Cache Statistics:**
   ```bash
   uv run python -c "from canary_mcp.server import get_cache_stats; import json; print(json.dumps(get_cache_stats(), indent=2))"
   ```

   **Monitor:**
   - Cache size (< max limit)
   - Hit rate trend
   - Entry count growth

3. **Circuit Breaker Health:**
   ```bash
   uv run python -c "from canary_mcp.server import get_health; result = get_health(); print(f'Circuit Breaker: {result[\"circuit_breakers\"][\"canary-api\"][\"state\"]}')"
   ```

   **Expected:** "closed" (healthy)

### Monthly Maintenance

1. **Clear old logs:**
   ```bash
   # Archive logs older than 30 days
   # Move to: logs/archive/
   ```

2. **Update dependencies:**
   ```bash
   uv sync --upgrade
   ```

3. **Run full test suite:**
   ```bash
   uv run pytest tests/integration/ -v
   ```

4. **Review user feedback:**
   - Collect queries that failed
   - Identify new use cases
   - Update example library

---

## Deployment Validation Checklist

Use this checklist to confirm successful deployment:

### Installation
- [ ] Repository cloned successfully
- [ ] Dependencies installed (`uv sync`)
- [ ] Validation script passes

### Configuration
- [ ] `.env` file created with site-specific values
- [ ] API credentials validated
- [ ] All required environment variables set

### Connection
- [ ] Ping tool responds
- [ ] Authentication successful
- [ ] Namespaces listed
- [ ] Tags searchable

### Performance
- [ ] Benchmark passes (median < 5s)
- [ ] Integration tests pass (7/7)
- [ ] Health check shows "healthy"

### User Access
- [ ] Claude Desktop configured
- [ ] User can query Canary data
- [ ] Example queries work
- [ ] Documentation shared

### Monitoring
- [ ] Log file created
- [ ] Metrics collection working
- [ ] Health check automated (optional)

---

## Support & Resources

### Documentation

- **API Reference:** `docs/API.md`
- **Example Queries:** `docs/examples.md`
- **Architecture:** `docs/architecture.md`
- **Troubleshooting:** `docs/troubleshooting/`

### Contact

For deployment issues:
1. Check troubleshooting guide above
2. Review logs: `logs/canary-mcp-server.log`
3. Run validation: `scripts/validate_installation.py`
4. Contact: [Your support contact]

---

**Deployment Guide Version:** 1.0
**Last Updated:** 2025-11-01
**Tested With:** Canary MCP Server v1.0.0

Generated with [Claude Code](https://claude.com/claude-code)
