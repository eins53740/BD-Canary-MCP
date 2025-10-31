"""Universal Canary MCP Server package."""

from canary_mcp.auth import CanaryAuthClient, CanaryAuthError, validate_config
from canary_mcp.server import main

__all__ = ["main", "CanaryAuthClient", "CanaryAuthError", "validate_config"]
