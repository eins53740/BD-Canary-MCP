"""Main MCP server module for Canary Historian integration."""

import os
from dotenv import load_dotenv
from fastmcp import FastMCP

# Load environment variables
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("Canary MCP Server")


@mcp.tool()
def ping() -> str:
    """
    Simple ping tool to test MCP server connectivity.

    Returns:
        str: Success message confirming server is responding
    """
    return "pong - Canary MCP Server is running!"


def main() -> None:
    """Run the MCP server."""
    # Get configuration from environment
    host = os.getenv("MCP_SERVER_HOST", "localhost")
    port = int(os.getenv("MCP_SERVER_PORT", "3000"))

    print(f"Starting Canary MCP Server on {host}:{port}")
    mcp.run()


if __name__ == "__main__":
    main()
