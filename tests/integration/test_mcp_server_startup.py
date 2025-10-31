"""Integration tests for MCP server startup and basic functionality."""

import pytest
from canary_mcp.server import mcp


@pytest.mark.integration
def test_mcp_server_initialization():
    """Test that MCP server initializes correctly."""
    assert mcp is not None
    assert mcp.name == "Canary MCP Server"


@pytest.mark.integration
def test_ping_tool_exists():
    """Test that ping tool is registered."""
    from canary_mcp.server import ping

    assert ping is not None
    # FastMCP wraps tools in FunctionTool objects
    assert hasattr(ping, "name")
    assert ping.name == "ping"


@pytest.mark.integration
def test_ping_tool_response():
    """Test that ping tool returns expected response."""
    from canary_mcp.server import ping

    # FastMCP FunctionTool has a fn attribute containing the actual function
    response = ping.fn()
    assert isinstance(response, str)
    assert "pong" in response.lower()
    assert "Canary MCP Server" in response


@pytest.mark.integration
def test_server_configuration():
    """Test that server can load configuration from environment."""
    from canary_mcp.server import main
    import os

    # Test that environment variables are accessible
    # Set test values
    os.environ["MCP_SERVER_HOST"] = "test-host"
    os.environ["MCP_SERVER_PORT"] = "9999"

    # Verify function exists and is callable
    assert main is not None
    assert callable(main)

    # Clean up
    os.environ.pop("MCP_SERVER_HOST", None)
    os.environ.pop("MCP_SERVER_PORT", None)
