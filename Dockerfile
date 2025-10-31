# Canary MCP Server - Dockerfile
# Multi-stage build for optimized production image

# Stage 1: Build stage
FROM python:3.13-slim as builder

# Set working directory
WORKDIR /build

# Install uv package manager
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install dependencies and build the package
RUN uv pip install --system -e .

# Stage 2: Runtime stage
FROM python:3.13-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # MCP server configuration
    MCP_SERVER_NAME="Canary MCP Server" \
    # Default log level (can be overridden)
    LOG_LEVEL=INFO

# Create non-root user for security
RUN groupadd -r -g 1000 mcpuser && \
    useradd -r -u 1000 -g mcpuser -d /app -s /bin/bash mcpuser

# Set working directory
WORKDIR /app

# Copy Python packages from builder stage
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=mcpuser:mcpuser src/ ./src/
COPY --chown=mcpuser:mcpuser pyproject.toml README.md ./

# Create logs directory with correct permissions
RUN mkdir -p /app/logs && chown -R mcpuser:mcpuser /app/logs

# Create directory for configuration
RUN mkdir -p /app/config && chown -R mcpuser:mcpuser /app/config

# Switch to non-root user
USER mcpuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import canary_mcp.server; print('healthy')" || exit 1

# Expose ports (if needed - MCP server typically uses stdio)
# EXPOSE 8000

# Set entrypoint to start MCP server
ENTRYPOINT ["python", "-m", "canary_mcp.server"]
