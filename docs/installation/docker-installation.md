# Docker Installation Guide

This guide explains how to install and run the Canary MCP Server using Docker. This installation method is ideal for:

- Production deployments
- Reproducible development environments
- Users with Docker Desktop access
- Environments requiring containerization

## Prerequisites

Before starting, ensure you have:

1. **Docker Desktop** installed (Windows, macOS, or Linux)
   - Download from: https://www.docker.com/products/docker-desktop/
   - Requires administrator privileges for installation
   - Minimum 4GB RAM allocated to Docker
   - At least 2GB free disk space

2. **Docker Compose** (included with Docker Desktop)
   - Verify installation: `docker-compose --version`

3. **Canary API Credentials**
   - SAF base URL
   - Views base URL
   - API token

## Installation Steps

### Step 1: Clone or Download the Project

```bash
git clone <repository-url>
cd canary-mcp-server
```

Or download and extract the project ZIP file.

### Step 2: Configure Environment Variables

Create a `.env` file in the project root directory:

```bash
# Copy the example file
copy .env.example .env
```

Edit `.env` file with your Canary credentials:

```env
# Canary API Configuration
CANARY_SAF_BASE_URL=https://your-canary-instance.com/api/saf
CANARY_VIEWS_BASE_URL=https://your-canary-instance.com/api/views
CANARY_API_TOKEN=your-api-token-here

# Logging Configuration
LOG_LEVEL=INFO

# Optional: Advanced Configuration
CANARY_SESSION_TIMEOUT_MS=30000
CANARY_REQUEST_TIMEOUT_SECONDS=30
CANARY_RETRY_ATTEMPTS=3
```

**Important**: Never commit the `.env` file to version control. It contains sensitive credentials.

### Step 3: Build the Docker Image

Build the Docker image from the project directory:

```bash
docker build -t canary-mcp-server .
```

**Options:**
- `-t canary-mcp-server`: Tags the image with a name
- `.`: Builds from current directory using Dockerfile

**Expected Output:**
```
[+] Building 45.2s (15/15) FINISHED
 => [internal] load build definition from Dockerfile
 => [internal] load .dockerignore
 => [stage-1 1/8] FROM docker.io/library/python:3.13-slim
 ...
 => => naming to docker.io/library/canary-mcp-server
```

**Build Time**: First build takes 2-5 minutes depending on network speed.

### Step 4: Start the Container

Start the MCP server using Docker Compose:

```bash
docker-compose up -d
```

**Options:**
- `-d`: Runs in detached mode (background)
- `--build`: Rebuilds the image before starting
- `--force-recreate`: Forces container recreation

**Expected Output:**
```
Creating network "canary-mcp-server_default" with the default driver
Creating canary-mcp-server ... done
```

### Step 5: Verify Container is Running

Check container status:

```bash
docker-compose ps
```

**Expected Output:**
```
Name                   Command               State   Ports
------------------------------------------------------------------
canary-mcp-server   python -m canary_mcp.server   Up (healthy)
```

**Status Indicators:**
- `Up (healthy)`: Container running and health check passing
- `Up (health: starting)`: Container starting, health check not ready
- `Exit 1`: Container failed to start (check logs)

### Step 6: View Logs

View container logs to verify startup:

```bash
# View all logs
docker-compose logs

# Follow logs in real-time
docker-compose logs -f

# View last 50 lines
docker-compose logs --tail=50

# View logs with timestamps
docker-compose logs -t
```

**Expected Log Output:**
```json
{"timestamp": "2025-10-31T10:00:00Z", "level": "info", "event": "server_starting"}
{"timestamp": "2025-10-31T10:00:01Z", "level": "info", "event": "auth_initialized"}
{"timestamp": "2025-10-31T10:00:01Z", "level": "info", "event": "server_ready"}
```

## Container Management

### Starting and Stopping

**Start container:**
```bash
docker-compose start
```

**Stop container:**
```bash
docker-compose stop
```

**Restart container:**
```bash
docker-compose restart
```

**Stop and remove container:**
```bash
docker-compose down
```

**Stop and remove container + volumes:**
```bash
docker-compose down -v
```

### Rebuilding After Code Changes

When you make code changes, rebuild and restart:

```bash
# Stop current container
docker-compose down

# Rebuild image
docker build -t canary-mcp-server .

# Start with new image
docker-compose up -d
```

**Shortcut:**
```bash
docker-compose up -d --build
```

### Updating Environment Variables

After changing `.env` file:

```bash
# Restart to load new variables
docker-compose restart
```

**Note**: Docker Compose automatically reads `.env` on restart.

## Volume Mounts

The Docker Compose configuration mounts two directories:

### Configuration Volume (Read-Only)

```yaml
volumes:
  - ./config:/app/config:ro
```

**Purpose**: Store additional configuration files
**Host Path**: `./config` (project root)
**Container Path**: `/app/config`
**Permissions**: Read-only (`:ro`)

### Logs Volume (Read-Write)

```yaml
volumes:
  - ./logs:/app/logs:rw
```

**Purpose**: Persist log files outside container
**Host Path**: `./logs` (project root)
**Container Path**: `/app/logs`
**Permissions**: Read-write (`:rw`)

**Accessing Logs:**
```bash
# View logs from host filesystem
type logs\server.log

# Or use Docker logs command
docker-compose logs -f
```

## Advanced Configuration

### Resource Limits

Adjust CPU and memory limits in `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'      # Maximum 2 CPU cores
      memory: 2G       # Maximum 2GB RAM
    reservations:
      cpus: '0.5'      # Reserved 0.5 CPU cores
      memory: 512M     # Reserved 512MB RAM
```

### Port Exposure (Optional)

If your MCP server needs network access, expose ports:

1. Edit `docker-compose.yml`:
```yaml
ports:
  - "8000:8000"  # host:container
```

2. Update `Dockerfile`:
```dockerfile
EXPOSE 8000
```

3. Restart container:
```bash
docker-compose up -d
```

### Custom Network

Create isolated network for multiple containers:

1. Edit `docker-compose.yml`:
```yaml
networks:
  mcp-network:
    driver: bridge

services:
  canary-mcp-server:
    networks:
      - mcp-network
```

2. Restart:
```bash
docker-compose down
docker-compose up -d
```

## Health Checks

The container includes automatic health monitoring:

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import canary_mcp.server; print('healthy')" || exit 1
```

**Parameters:**
- `--interval=30s`: Check every 30 seconds
- `--timeout=10s`: Timeout after 10 seconds
- `--retries=3`: Mark unhealthy after 3 failures

**Check Health Status:**
```bash
docker inspect --format='{{.State.Health.Status}}' canary-mcp-server
```

**Possible Statuses:**
- `healthy`: Container is healthy
- `unhealthy`: Health check failing
- `starting`: Initial grace period

## Troubleshooting

### Issue 1: Container Fails to Start

**Symptoms:**
```bash
docker-compose ps
# Shows: Exit 1 or Exit 137
```

**Diagnosis:**
```bash
docker-compose logs
```

**Common Causes:**
1. Missing environment variables in `.env`
2. Invalid API token
3. Insufficient memory allocated to Docker
4. Port conflicts (if ports are exposed)

**Solution:**
1. Verify `.env` file exists and has all required variables
2. Check Docker Desktop has at least 2GB RAM allocated
3. Run validation: `docker run --rm canary-mcp-server python -c "import canary_mcp.server"`

### Issue 2: Permission Denied on Volumes

**Symptoms:**
```
PermissionError: [Errno 13] Permission denied: '/app/logs/server.log'
```

**Cause:** Volume mount permissions conflict

**Solution (Windows):**
```bash
# Ensure logs directory exists with correct permissions
mkdir logs
icacls logs /grant Users:(OI)(CI)F
```

**Solution (Linux/macOS):**
```bash
# Ensure directory is writable
mkdir -p logs
chmod 755 logs
```

### Issue 3: Changes Not Reflected After Rebuild

**Symptoms:** Code changes don't appear in running container

**Cause:** Using cached image layers

**Solution:**
```bash
# Force complete rebuild without cache
docker-compose down
docker build --no-cache -t canary-mcp-server .
docker-compose up -d
```

### Issue 4: Health Check Failing

**Symptoms:**
```bash
docker-compose ps
# Shows: Up (unhealthy)
```

**Diagnosis:**
```bash
# Check detailed health status
docker inspect canary-mcp-server | findstr -i health
```

**Solution:**
1. Check logs for startup errors: `docker-compose logs`
2. Verify dependencies installed: `docker exec canary-mcp-server pip list`
3. Test import manually: `docker exec canary-mcp-server python -c "import canary_mcp.server"`

### Issue 5: Cannot Connect to Canary API

**Symptoms:**
```json
{"level": "error", "event": "connection_failed", "error": "Network unreachable"}
```

**Cause:** Container network isolation

**Solution:**
1. Verify host can reach Canary API:
```bash
curl https://your-canary-instance.com/api/saf
```

2. If using VPN, ensure Docker can access network:
   - Docker Desktop → Settings → Resources → Network
   - Check "Use kernel networking for UDP"

3. Test from container:
```bash
docker exec canary-mcp-server curl https://your-canary-instance.com/api/saf
```

### Issue 6: Docker Build Fails

**Symptoms:**
```
ERROR [stage-1 5/10] RUN uv pip install --system -e .
```

**Cause:** Network issues or dependency conflicts

**Solution:**
1. Check internet connectivity
2. Clear Docker build cache:
```bash
docker builder prune -a
```

3. Rebuild with verbose output:
```bash
docker build --progress=plain -t canary-mcp-server .
```

### Issue 7: Container Uses Too Much Memory

**Symptoms:** System slowdown, Docker Desktop high memory usage

**Solution:**
1. Check current usage:
```bash
docker stats canary-mcp-server
```

2. Reduce memory limits in `docker-compose.yml`:
```yaml
deploy:
  resources:
    limits:
      memory: 1G  # Reduce from 2G to 1G
```

3. Restart:
```bash
docker-compose down
docker-compose up -d
```

### Issue 8: Logs Directory Fills Up

**Symptoms:** Disk space warnings, large log files

**Solution:**
Log rotation is configured automatically in `docker-compose.yml`:

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"   # Max 10MB per log file
    max-file: "3"     # Keep 3 files (total 30MB)
```

**Manual Cleanup:**
```bash
# View log size
docker-compose logs --tail=0 | measure-object -Line

# Truncate logs
docker-compose down
Remove-Item logs\*.log
docker-compose up -d
```

## Diagnostic Commands

### Container Information

```bash
# View all container details
docker inspect canary-mcp-server

# Check resource usage
docker stats canary-mcp-server

# View container processes
docker top canary-mcp-server

# Execute command in container
docker exec -it canary-mcp-server bash
```

### Image Information

```bash
# List all images
docker images

# View image history
docker history canary-mcp-server

# View image size breakdown
docker image inspect canary-mcp-server --format='{{.Size}}'
```

### Network Diagnostics

```bash
# List networks
docker network ls

# Inspect network
docker network inspect canary-mcp-server_default

# Test connectivity from container
docker exec canary-mcp-server ping google.com
```

## Uninstallation

To completely remove the Docker installation:

```bash
# Stop and remove container
docker-compose down

# Remove Docker image
docker rmi canary-mcp-server

# Remove volumes (optional - deletes logs)
docker volume prune

# Remove networks (optional)
docker network prune

# Delete project files (optional)
cd ..
Remove-Item -Recurse -Force canary-mcp-server
```

## Next Steps

After successful installation:

1. **Test the MCP server**: Run connectivity tests
2. **Configure Claude Desktop**: Add MCP server to configuration
3. **Explore MCP tools**: Test available tools and resources
4. **Set up monitoring**: Configure log aggregation if needed

## Additional Resources

- Docker Documentation: https://docs.docker.com/
- Docker Compose Reference: https://docs.docker.com/compose/
- MCP Server Documentation: See main README.md
- Troubleshooting Guide: See `docs/installation/troubleshooting.md`

## Comparison with Non-Admin Installation

| Feature | Docker Installation | Non-Admin Installation |
|---------|--------------------|-----------------------|
| **Prerequisites** | Docker Desktop (requires admin) | Python 3.13 portable (no admin) |
| **Installation Time** | 5-10 minutes | 10-15 minutes |
| **Isolation** | Complete containerization | Process-level |
| **Reproducibility** | Identical across environments | Depends on host configuration |
| **Resource Usage** | Higher (Docker overhead) | Lower (native process) |
| **Updates** | Rebuild image | Update packages |
| **Best For** | Production, DevOps workflows | Company workstations, dev laptops |

Choose Docker if you need reproducible deployments or are already using containerization. Choose non-admin installation for simplicity and lower resource usage on Windows workstations.
