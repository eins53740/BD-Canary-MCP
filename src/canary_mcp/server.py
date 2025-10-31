"""Main MCP server module for Canary Historian integration."""

import asyncio
import os
from typing import Any

import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP

from canary_mcp.auth import CanaryAuthClient, CanaryAuthError, validate_config

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


@mcp.tool()
async def search_tags(search_pattern: str) -> dict[str, Any]:
    """
    Search for Canary tags by name pattern.

    This tool searches for industrial process tags in the Canary historian
    that match the provided search pattern.

    Args:
        search_pattern: Tag name or pattern to search for (supports wildcards)

    Returns:
        dict[str, Any]: Dictionary containing search results with keys:
            - tags: List of matching tags with metadata
            - count: Total number of tags found
            - success: Boolean indicating if operation succeeded
            - pattern: The search pattern used

    Raises:
        Exception: If authentication fails or API request errors occur
    """
    try:
        # Validate search pattern
        if not search_pattern or not search_pattern.strip():
            return {
                "success": False,
                "error": "Search pattern cannot be empty",
                "tags": [],
                "count": 0,
                "pattern": search_pattern,
            }

        # Get Canary Views base URL from environment
        views_base_url = os.getenv("CANARY_VIEWS_BASE_URL", "")
        if not views_base_url:
            raise ValueError("CANARY_VIEWS_BASE_URL not configured")

        # Authenticate and get session token
        async with CanaryAuthClient() as client:
            session_token = await client.get_valid_token()

            # Query Canary API for tag search
            # Using browseTags endpoint to search for tags
            search_url = f"{views_base_url}/api/v1/browseTags"

            async with httpx.AsyncClient(timeout=10.0) as http_client:
                response = await http_client.post(
                    search_url,
                    json={
                        "sessionToken": session_token,
                        "searchPattern": search_pattern,
                        "includeProperties": True,
                    },
                )

                response.raise_for_status()
                data = response.json()

                # Parse tag data from response
                tags = []
                if isinstance(data, dict) and "tags" in data:
                    tag_list = data.get("tags", [])
                    for tag in tag_list:
                        if isinstance(tag, dict):
                            tags.append(
                                {
                                    "name": tag.get("name", ""),
                                    "path": tag.get("path", tag.get("name", "")),
                                    "dataType": tag.get("dataType", "unknown"),
                                    "description": tag.get("description", ""),
                                }
                            )

                return {
                    "success": True,
                    "tags": tags,
                    "count": len(tags),
                    "pattern": search_pattern,
                }

    except CanaryAuthError as e:
        error_msg = f"Authentication failed: {str(e)}"
        return {
            "success": False,
            "error": error_msg,
            "tags": [],
            "count": 0,
            "pattern": search_pattern,
        }

    except httpx.HTTPStatusError as e:
        error_msg = (
            f"API request failed with status {e.response.status_code}: {e.response.text}"
        )
        return {
            "success": False,
            "error": error_msg,
            "tags": [],
            "count": 0,
            "pattern": search_pattern,
        }

    except httpx.RequestError as e:
        error_msg = f"Network error accessing Canary API: {str(e)}"
        return {
            "success": False,
            "error": error_msg,
            "tags": [],
            "count": 0,
            "pattern": search_pattern,
        }

    except Exception as e:
        error_msg = f"Unexpected error searching tags: {str(e)}"
        return {
            "success": False,
            "error": error_msg,
            "tags": [],
            "count": 0,
            "pattern": search_pattern,
        }


@mcp.tool()
async def get_tag_metadata(tag_path: str) -> dict[str, Any]:
    """
    Get detailed metadata for a specific tag in Canary.

    This tool retrieves comprehensive metadata for a tag including properties,
    data type, units, description, and configuration details.

    Args:
        tag_path: Full path or name of the tag to retrieve metadata for

    Returns:
        dict[str, Any]: Dictionary containing tag metadata with keys:
            - metadata: Dictionary of tag properties
            - success: Boolean indicating if operation succeeded
            - tag_path: The tag path that was queried

    Raises:
        Exception: If authentication fails or API request errors occur
    """
    try:
        # Validate tag path
        if not tag_path or not tag_path.strip():
            return {
                "success": False,
                "error": "Tag path cannot be empty",
                "metadata": {},
                "tag_path": tag_path,
            }

        # Get Canary Views base URL from environment
        views_base_url = os.getenv("CANARY_VIEWS_BASE_URL", "")
        if not views_base_url:
            raise ValueError("CANARY_VIEWS_BASE_URL not configured")

        # Authenticate and get session token
        async with CanaryAuthClient() as client:
            session_token = await client.get_valid_token()

            # Query Canary API for tag metadata
            # Using getTagProperties endpoint to get detailed metadata
            metadata_url = f"{views_base_url}/api/v1/getTagProperties"

            async with httpx.AsyncClient(timeout=10.0) as http_client:
                response = await http_client.post(
                    metadata_url,
                    json={
                        "sessionToken": session_token,
                        "tagPath": tag_path,
                    },
                )

                response.raise_for_status()
                data = response.json()

                # Parse metadata from response
                metadata = {}
                if isinstance(data, dict):
                    # Extract common metadata fields
                    metadata = {
                        "name": data.get("name", data.get("tagName", "")),
                        "path": data.get("path", data.get("tagPath", tag_path)),
                        "dataType": data.get("dataType", data.get("type", "unknown")),
                        "description": data.get("description", ""),
                        "units": data.get("units", data.get("engineeringUnits", "")),
                        "minValue": data.get("minValue", data.get("min")),
                        "maxValue": data.get("maxValue", data.get("max")),
                        "updateRate": data.get("updateRate", data.get("scanRate")),
                    }

                    # Include any additional properties
                    properties = data.get("properties", {})
                    if properties and isinstance(properties, dict):
                        metadata["properties"] = properties

                return {
                    "success": True,
                    "metadata": metadata,
                    "tag_path": tag_path,
                }

    except CanaryAuthError as e:
        error_msg = f"Authentication failed: {str(e)}"
        return {
            "success": False,
            "error": error_msg,
            "metadata": {},
            "tag_path": tag_path,
        }

    except httpx.HTTPStatusError as e:
        error_msg = (
            f"API request failed with status {e.response.status_code}: {e.response.text}"
        )
        return {
            "success": False,
            "error": error_msg,
            "metadata": {},
            "tag_path": tag_path,
        }

    except httpx.RequestError as e:
        error_msg = f"Network error accessing Canary API: {str(e)}"
        return {
            "success": False,
            "error": error_msg,
            "metadata": {},
            "tag_path": tag_path,
        }

    except Exception as e:
        error_msg = f"Unexpected error retrieving tag metadata: {str(e)}"
        return {
            "success": False,
            "error": error_msg,
            "metadata": {},
            "tag_path": tag_path,
        }


@mcp.tool()
async def list_namespaces() -> dict[str, Any]:
    """
    List available Canary namespaces from the historian.

    This tool retrieves the hierarchical organization of industrial process tags
    by querying the Canary Views API for namespace information.

    Returns:
        dict[str, Any]: Dictionary containing namespace structure with keys:
            - namespaces: List of namespace paths
            - count: Total number of namespaces found
            - success: Boolean indicating if operation succeeded

    Raises:
        Exception: If authentication fails or API request errors occur
    """
    try:
        # Get Canary Views base URL from environment
        views_base_url = os.getenv("CANARY_VIEWS_BASE_URL", "")
        if not views_base_url:
            raise ValueError("CANARY_VIEWS_BASE_URL not configured")

        # Authenticate and get session token
        async with CanaryAuthClient() as client:
            session_token = await client.get_valid_token()

            # Query Canary API for namespace/node information
            # Using browseNodes endpoint to get hierarchical structure
            browse_url = f"{views_base_url}/api/v1/browseNodes"

            async with httpx.AsyncClient(timeout=10.0) as http_client:
                response = await http_client.post(
                    browse_url,
                    json={
                        "sessionToken": session_token,
                        "nodeId": "",  # Empty for root level
                        "recursive": True,  # Get full hierarchy
                    },
                )

                response.raise_for_status()
                data = response.json()

                # Parse namespace data from response
                namespaces = []
                if isinstance(data, dict) and "nodes" in data:
                    nodes = data.get("nodes", [])
                    for node in nodes:
                        if isinstance(node, dict) and "path" in node:
                            namespaces.append(node["path"])

                return {
                    "success": True,
                    "namespaces": namespaces,
                    "count": len(namespaces),
                }

    except CanaryAuthError as e:
        error_msg = f"Authentication failed: {str(e)}"
        return {"success": False, "error": error_msg, "namespaces": [], "count": 0}

    except httpx.HTTPStatusError as e:
        error_msg = f"API request failed with status {e.response.status_code}: {e.response.text}"
        return {"success": False, "error": error_msg, "namespaces": [], "count": 0}

    except httpx.RequestError as e:
        error_msg = f"Network error accessing Canary API: {str(e)}"
        return {"success": False, "error": error_msg, "namespaces": [], "count": 0}

    except Exception as e:
        error_msg = f"Unexpected error listing namespaces: {str(e)}"
        return {"success": False, "error": error_msg, "namespaces": [], "count": 0}


def main() -> None:
    """Run the MCP server."""
    # Validate configuration before starting server
    try:
        asyncio.run(validate_config())
    except Exception as e:
        print(f"Configuration validation failed: {e}")
        print("Please check your .env file and ensure all required variables are set.")
        return

    # Get configuration from environment
    host = os.getenv("MCP_SERVER_HOST", "localhost")
    port = int(os.getenv("MCP_SERVER_PORT", "3000"))

    print(f"Starting Canary MCP Server on {host}:{port}")
    mcp.run()


if __name__ == "__main__":
    main()
