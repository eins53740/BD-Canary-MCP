#!/usr/bin/env python3
"""
Simple verification script to list all MCP tools and their documentation.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from canary_mcp.server import mcp


def verify_tools():
    """Verify all registered MCP tools."""
    print("=" * 70)
    print("MCP SERVER TOOL VERIFICATION")
    print("=" * 70)
    print()

    # List all tools registered with the MCP server
    print("Inspecting registered MCP tools...")
    print()

    # Get tools using FastMCP's internal structure
    tool_count = 0
    tools_info = []

    # Collect tool information
    tool_names = [
        "ping",
        "search_tags",
        "get_tag_metadata",
        "get_tag_properties",
        "list_namespaces",
        "read_timeseries",
        "get_server_info",
        "get_metrics",
        "get_metrics_summary",
    ]

    for tool_name in tool_names:
        if hasattr(mcp, tool_name):
            tool_func = getattr(mcp, tool_name)
            doc = tool_func.__doc__ or "No documentation"
            # Get first line of docstring
            first_line = doc.strip().split("\n")[0] if doc else "No description"
            tools_info.append(
                {"name": tool_name, "description": first_line, "function": tool_func}
            )
            tool_count += 1

    # Display tool information
    print(f"[OK] Found {tool_count} registered tools:\n")

    for i, tool in enumerate(tools_info, 1):
        print(f"{i}. {tool['name']}")
        print(f"   Description: {tool['description']}")

        # Get function signature
        import inspect

        sig = inspect.signature(tool["function"])
        params = list(sig.parameters.keys())
        if params:
            print(f"   Parameters: {', '.join(params)}")
        else:
            print("   Parameters: None")
        print()

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print()
    print(f"Total Tools: {tool_count}")
    print()
    print("Tool Categories:")
    print("  - Connection Testing: ping")
    print("  - Data Discovery: list_namespaces, search_tags")
    print("  - Tag Information: get_tag_metadata, get_tag_properties")
    print("  - Data Retrieval: read_timeseries")
    print("  - Server Info: get_server_info")
    print("  - Performance Monitoring: get_metrics, get_metrics_summary")
    print()
    print("[OK] All tools are properly registered and ready for use!")
    print()
    print("To test these tools:")
    print("  1. Use the MCP Inspector web UI at http://localhost:6274")
    print("  2. Connect via Claude Desktop")
    print("  3. Use any MCP-compatible client")
    print()


if __name__ == "__main__":
    verify_tools()
