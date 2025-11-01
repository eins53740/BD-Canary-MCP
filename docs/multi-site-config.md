# Multi-Site Configuration Guide

**Story 2.5: Multi-Site Configuration Management**

This guide explains how to deploy the Canary MCP Server across multiple Canary sites with site-specific configurations.

## Overview

The MCP server supports multiple deployment models:
- **Single-site deployment**: One MCP server instance per Canary site
- **Multi-site deployment**: Multiple MCP server instances, each configured for a different site

## Single-Site Configuration

The standard deployment uses environment variables from `.env`:

```bash
CANARY_SAF_BASE_URL=https://site1.example.com:55236/api/v1
CANARY_VIEWS_BASE_URL=https://site1.example.com:55236
CANARY_API_TOKEN=site1-token-here
```

## Multi-Site Deployment Options

### Option 1: Multiple .env Files (Recommended)

Create separate `.env` files for each site:

**Structure:**
```
project/
├── .env.site1
├── .env.site2
├── .env.site3
└── scripts/
    ├── start-site1.sh
    ├── start-site2.sh
    └── start-site3.sh
```

**Example .env.site1:**
```bash
# Site 1: Maceira Plant
CANARY_SAF_BASE_URL=https://maceira-canary.secil.pt:55236/api/v1
CANARY_VIEWS_BASE_URL=https://maceira-canary.secil.pt:55236
CANARY_API_TOKEN=maceira-token-xyz
CANARY_POOL_SIZE=10
CANARY_TIMEOUT=30
CANARY_CACHE_DIR=.cache/maceira
```

**Example .env.site2:**
```bash
# Site 2: Outão Plant
CANARY_SAF_BASE_URL=https://outao-canary.secil.pt:55236/api/v1
CANARY_VIEWS_BASE_URL=https://outao-canary.secil.pt:55236
CANARY_API_TOKEN=outao-token-abc
CANARY_POOL_SIZE=10
CANARY_TIMEOUT=30
CANARY_CACHE_DIR=.cache/outao
```

**Startup Script (start-site1.sh):**
```bash
#!/bin/bash
# Load site-specific environment
export $(cat .env.site1 | xargs)

# Start MCP server
python -m canary_mcp
```

### Option 2: Docker Compose Multi-Site

Use Docker Compose to run multiple instances:

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  mcp-maceira:
    build: .
    env_file:
      - .env.site1
    container_name: canary-mcp-maceira
    restart: unless-stopped
    volumes:
      - ./cache-maceira:/app/.cache

  mcp-outao:
    build: .
    env_file:
      - .env.site2
    container_name: canary-mcp-outao
    restart: unless-stopped
    volumes:
      - ./cache-outao:/app/.cache

  mcp-cibra:
    build: .
    env_file:
      - .env.site3
    container_name: canary-mcp-cibra
    restart: unless-stopped
    volumes:
      - ./cache-cibra:/app/.cache
```

**Start all sites:**
```bash
docker-compose up -d
```

### Option 3: Kubernetes Multi-Site

For large deployments, use Kubernetes with ConfigMaps:

**configmap-site1.yaml:**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: canary-mcp-site1-config
data:
  CANARY_SAF_BASE_URL: "https://maceira-canary.secil.pt:55236/api/v1"
  CANARY_VIEWS_BASE_URL: "https://maceira-canary.secil.pt:55236"
  CANARY_POOL_SIZE: "10"
  CANARY_TIMEOUT: "30"
  CANARY_CACHE_DIR: "/app/.cache"
```

**deployment-site1.yaml:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: canary-mcp-maceira
spec:
  replicas: 1
  selector:
    matchLabels:
      app: canary-mcp
      site: maceira
  template:
    metadata:
      labels:
        app: canary-mcp
        site: maceira
    spec:
      containers:
      - name: canary-mcp
        image: canary-mcp:latest
        envFrom:
        - configMapRef:
            name: canary-mcp-site1-config
        - secretRef:
            name: canary-mcp-site1-secrets
```

## Site-Specific Tuning

Different sites may require different performance settings:

### High-Load Site (e.g., Main Production Plant)
```bash
CANARY_POOL_SIZE=20              # More concurrent connections
CANARY_TIMEOUT=45                # Longer timeout for complex queries
CANARY_CACHE_MAX_SIZE_MB=200     # Larger cache
CANARY_CACHE_METADATA_TTL=7200   # 2 hour cache for stable metadata
```

### Low-Load Site (e.g., Small Regional Plant)
```bash
CANARY_POOL_SIZE=5               # Fewer connections
CANARY_TIMEOUT=30                # Standard timeout
CANARY_CACHE_MAX_SIZE_MB=50      # Smaller cache
CANARY_CACHE_METADATA_TTL=3600   # 1 hour cache
```

### Development/Test Site
```bash
CANARY_POOL_SIZE=3
CANARY_TIMEOUT=15
CANARY_CACHE_MAX_SIZE_MB=25
CANARY_RETRY_ATTEMPTS=3
LOG_LEVEL=DEBUG                  # Verbose logging for troubleshooting
```

## Configuration Validation

Before deploying to a site, validate the configuration:

```bash
# Set environment for site
export $(cat .env.site1 | xargs)

# Run validation script
python scripts/validate_installation.py
```

Expected output:
```
✓ Configuration valid
✓ Canary API accessible
✓ Authentication successful
✓ Cache directory writable
✓ Performance meets requirements
```

## Monitoring Multi-Site Deployments

Each site should be monitored independently:

1. **Metrics Collection**: Each instance exports metrics at `/metrics`
2. **Log Aggregation**: Centralize logs with site identifier
3. **Health Checks**: Regular health endpoint checks
4. **Performance Baselines**: Track per-site performance trends

## Troubleshooting

### Site-Specific Connection Issues

If one site fails while others work:

1. Check site-specific `.env` file for correct URLs
2. Verify network connectivity to that site's Canary server
3. Confirm API token is valid for that site
4. Review site-specific logs

### Cache Isolation

Each site should have its own cache directory to prevent conflicts:

```bash
# Site 1
CANARY_CACHE_DIR=.cache/site1

# Site 2
CANARY_CACHE_DIR=.cache/site2
```

## Best Practices

1. **Separate Caches**: Use different cache directories per site
2. **Site Labeling**: Include site name in log entries for debugging
3. **Staged Rollout**: Deploy to one site first, verify, then scale
4. **Configuration Backup**: Keep `.env.site*` files in version control (without tokens)
5. **Secret Management**: Use secret managers (e.g., HashiCorp Vault) for tokens in production

## Example: 6-Site Deployment

For the target 6-site rollout mentioned in the PRD:

**Sites:**
1. Maceira (main production)
2. Outão (production)
3. Cibra-Pataias (production)
4. Loulé (production)
5. São Miguel (regional)
6. Development/Test

**Deployment Plan:**
```bash
# Phase 1: Deploy to test site
./deploy-site.sh site6-test

# Phase 2: Deploy to one production site (pilot)
./deploy-site.sh site1-maceira

# Phase 3: Monitor for 48 hours, validate performance

# Phase 4: Deploy to remaining sites
./deploy-site.sh site2-outao
./deploy-site.sh site3-cibra
./deploy-site.sh site4-loule
./deploy-site.sh site5-sao-miguel
```

## Summary

The Canary MCP Server is designed for flexible multi-site deployment:
- **Recommended**: Multiple instances with site-specific `.env` files
- **Scalable**: Docker Compose or Kubernetes for orchestration
- **Tunable**: Site-specific performance and cache settings
- **Monitorable**: Independent metrics and logs per site

For assistance with multi-site deployment, refer to the [Deployment Guide](./installation/deployment-guide.md).
