#!/usr/bin/env python3
"""Test Canary API connection with real token."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from canary_mcp.server import get_server_info


async def test_connection():
    """Test connection to Canary server."""
    print("Testing Canary API connection...")
    print("-" * 60)

    try:
        # Test get_server_info tool
        result = await get_server_info.fn()

        if result.get("success"):
            print("\n[OK] Connection successful!")
            print("\nServer Information:")
            server_info = result.get("server_info", {})
            print(f"  Canary Server URL: {server_info.get('canary_server_url')}")
            print(f"  API Version: {server_info.get('api_version')}")
            print(f"  Connected: {server_info.get('connected')}")
            print(f"  Supported Timezones: {server_info.get('total_timezones')} total")
            print(
                f"  Supported Aggregates: {server_info.get('total_aggregates')} total"
            )

            mcp_info = result.get("mcp_info", {})
            print("\nMCP Server:")
            print(f"  Name: {mcp_info.get('server_name')}")
            print(f"  Version: {mcp_info.get('version')}")

            print("\n[OK] Your MCP server is ready to use in Claude Desktop!")
            return 0
        else:
            print("\n[ERROR] Connection failed!")
            print(f"Error: {result.get('error', 'Unknown error')}")
            print("\nPlease check:")
            print("  1. Your API token is valid")
            print("  2. The Canary server URL is correct")
            print("  3. You have network access to the Canary server")
            return 1

    except Exception as e:
        print(f"\n[ERROR] Connection test failed: {e}")
        print("\nPlease verify:")
        print("  1. CANARY_API_TOKEN is set correctly in .env")
        print("  2. CANARY_VIEWS_BASE_URL is accessible from your network")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(test_connection())
    sys.exit(exit_code)
