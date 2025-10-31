"""Main MCP server module for Canary Historian integration."""

import os
from datetime import datetime, timedelta
from typing import Any

import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP

from canary_mcp.auth import CanaryAuthError, CanaryAuthClient
from canary_mcp.logging_setup import configure_logging, get_logger
from canary_mcp.request_context import set_request_id, get_request_id

# Load environment variables
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("Canary MCP Server")

# Get logger instance
log = get_logger(__name__)


def parse_time_expression(time_expr: str) -> str:
    """
    Parse natural language time expressions into ISO timestamps.

    Supports expressions like:
    - "yesterday" → previous calendar day
    - "last week" → past 7 days
    - "past 24 hours" → last 24 hours from now
    - "last 30 days" → past 30 days from now

    Args:
        time_expr: Natural language time expression or ISO timestamp

    Returns:
        str: ISO timestamp string

    Raises:
        ValueError: If expression cannot be parsed
    """
    time_expr_lower = time_expr.lower().strip()
    now = datetime.utcnow()

    # Try parsing as ISO timestamp first
    try:
        datetime.fromisoformat(time_expr.replace("Z", "+00:00"))
        return time_expr  # Already ISO format
    except (ValueError, AttributeError):
        pass

    # Natural language expressions
    if time_expr_lower == "yesterday":
        target = now - timedelta(days=1)
        return target.replace(hour=0, minute=0, second=0, microsecond=0).isoformat() + "Z"

    if "last week" in time_expr_lower or "past week" in time_expr_lower:
        target = now - timedelta(days=7)
        return target.isoformat() + "Z"

    if "past 24 hours" in time_expr_lower or "last 24 hours" in time_expr_lower:
        target = now - timedelta(hours=24)
        return target.isoformat() + "Z"

    if "last 30 days" in time_expr_lower or "past 30 days" in time_expr_lower:
        target = now - timedelta(days=30)
        return target.isoformat() + "Z"

    if "last 7 days" in time_expr_lower or "past 7 days" in time_expr_lower:
        target = now - timedelta(days=7)
        return target.isoformat() + "Z"

    if time_expr_lower == "now":
        return now.isoformat() + "Z"

    # If not recognized, raise error
    raise ValueError(f"Unrecognized time expression: {time_expr}")


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
    request_id = set_request_id()
    log.info(
        "search_tags_called",
        search_pattern=search_pattern,
        request_id=request_id,
        tool="search_tags",
    )

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

        # Authenticate and get API token
        async with CanaryAuthClient() as client:
            api_token = await client.get_valid_token()

            # Query Canary API for tag search
            # Using browseTags endpoint to search for tags
            search_url = f"{views_base_url}/api/v2/browseTags"

            async with httpx.AsyncClient(timeout=10.0) as http_client:
                response = await http_client.post(
                    search_url,
                    json={
                        "apiToken": api_token,
                        "search": search_pattern,
                        "deep": True,
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

                log.info(
                    "search_tags_success",
                    pattern=search_pattern,
                    tag_count=len(tags),
                    request_id=get_request_id(),
                )
                return {
                    "success": True,
                    "tags": tags,
                    "count": len(tags),
                    "pattern": search_pattern,
                }

    except CanaryAuthError as e:
        error_msg = f"Authentication failed: {str(e)}"
        log.error(
            "search_tags_auth_failed",
            error=error_msg,
            pattern=search_pattern,
            request_id=get_request_id(),
        )
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
        log.error(
            "search_tags_api_error",
            error=error_msg,
            status_code=e.response.status_code,
            pattern=search_pattern,
            request_id=get_request_id(),
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
        log.error(
            "search_tags_network_error",
            error=error_msg,
            pattern=search_pattern,
            request_id=get_request_id(),
        )
        return {
            "success": False,
            "error": error_msg,
            "tags": [],
            "count": 0,
            "pattern": search_pattern,
        }

    except Exception as e:
        error_msg = f"Unexpected error searching tags: {str(e)}"
        log.error(
            "search_tags_unexpected_error",
            error=error_msg,
            pattern=search_pattern,
            request_id=get_request_id(),
            exc_info=True,
        )
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
    request_id = set_request_id()
    log.info(
        "get_tag_metadata_called",
        tag_path=tag_path,
        request_id=request_id,
        tool="get_tag_metadata",
    )

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

        # Authenticate and get API token
        async with CanaryAuthClient() as client:
            api_token = await client.get_valid_token()

            # Query Canary API for tag metadata
            # Using getTagProperties endpoint to get detailed metadata
            metadata_url = f"{views_base_url}/api/v2/getTagProperties"

            async with httpx.AsyncClient(timeout=10.0) as http_client:
                response = await http_client.post(
                    metadata_url,
                    json={
                        "apiToken": api_token,
                        "tags": [tag_path],
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

                log.info(
                    "get_tag_metadata_success",
                    tag_path=tag_path,
                    data_type=metadata.get("dataType"),
                    units=metadata.get("units"),
                    request_id=get_request_id(),
                )
                return {
                    "success": True,
                    "metadata": metadata,
                    "tag_path": tag_path,
                }

    except CanaryAuthError as e:
        error_msg = f"Authentication failed: {str(e)}"
        log.error(
            "get_tag_metadata_auth_failed",
            error=error_msg,
            tag_path=tag_path,
            request_id=get_request_id(),
        )
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
        log.error(
            "get_tag_metadata_api_error",
            error=error_msg,
            status_code=e.response.status_code,
            tag_path=tag_path,
            request_id=get_request_id(),
        )
        return {
            "success": False,
            "error": error_msg,
            "metadata": {},
            "tag_path": tag_path,
        }

    except httpx.RequestError as e:
        error_msg = f"Network error accessing Canary API: {str(e)}"
        log.error(
            "get_tag_metadata_network_error",
            error=error_msg,
            tag_path=tag_path,
            request_id=get_request_id(),
        )
        return {
            "success": False,
            "error": error_msg,
            "metadata": {},
            "tag_path": tag_path,
        }

    except Exception as e:
        error_msg = f"Unexpected error retrieving tag metadata: {str(e)}"
        log.error(
            "get_tag_metadata_unexpected_error",
            error=error_msg,
            tag_path=tag_path,
            request_id=get_request_id(),
            exc_info=True,
        )
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
    request_id = set_request_id()
    log.info("list_namespaces_called", request_id=request_id, tool="list_namespaces")

    try:
        # Get Canary Views base URL from environment
        views_base_url = os.getenv("CANARY_VIEWS_BASE_URL", "")
        if not views_base_url:
            raise ValueError("CANARY_VIEWS_BASE_URL not configured")

        # Authenticate and get API token
        async with CanaryAuthClient() as client:
            api_token = await client.get_valid_token()

            # Query Canary API for namespace/node information
            # Using browseNodes endpoint to get hierarchical structure
            browse_url = f"{views_base_url}/api/v2/browseNodes"

            async with httpx.AsyncClient(timeout=10.0) as http_client:
                response = await http_client.post(
                    browse_url,
                    json={
                        "apiToken": api_token,
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

                log.info(
                    "list_namespaces_success",
                    namespace_count=len(namespaces),
                    request_id=get_request_id(),
                )
                return {
                    "success": True,
                    "namespaces": namespaces,
                    "count": len(namespaces),
                }

    except CanaryAuthError as e:
        error_msg = f"Authentication failed: {str(e)}"
        log.error("list_namespaces_auth_failed", error=error_msg, request_id=get_request_id())
        return {"success": False, "error": error_msg, "namespaces": [], "count": 0}

    except httpx.HTTPStatusError as e:
        error_msg = f"API request failed with status {e.response.status_code}: {e.response.text}"
        log.error(
            "list_namespaces_api_error",
            error=error_msg,
            status_code=e.response.status_code,
            request_id=get_request_id(),
        )
        return {"success": False, "error": error_msg, "namespaces": [], "count": 0}

    except httpx.RequestError as e:
        error_msg = f"Network error accessing Canary API: {str(e)}"
        log.error("list_namespaces_network_error", error=error_msg, request_id=get_request_id())
        return {"success": False, "error": error_msg, "namespaces": [], "count": 0}

    except Exception as e:
        error_msg = f"Unexpected error listing namespaces: {str(e)}"
        log.error(
            "list_namespaces_unexpected_error",
            error=error_msg,
            request_id=get_request_id(),
            exc_info=True,
        )
        return {"success": False, "error": error_msg, "namespaces": [], "count": 0}


@mcp.tool()
async def read_timeseries(
    tag_names: str | list[str],
    start_time: str,
    end_time: str,
    page_size: int = 1000,
) -> dict[str, Any]:
    """
    Retrieve historical timeseries data for specific tags and time ranges.

    This tool retrieves historical process data from the Canary historian
    for analysis and troubleshooting.

    Args:
        tag_names: Single tag name or list of tag names to retrieve data for
        start_time: Start time (ISO timestamp or natural language like "yesterday")
        end_time: End time (ISO timestamp or natural language like "now")
        page_size: Number of samples per page (default 1000)

    Returns:
        dict[str, Any]: Dictionary containing timeseries data with keys:
            - data: List of data points with timestamp, value, quality
            - count: Total number of data points returned
            - success: Boolean indicating if operation succeeded
            - tag_names: The tag names that were queried
            - start_time: Parsed start time (ISO format)
            - end_time: Parsed end time (ISO format)

    Raises:
        Exception: If authentication fails or API request errors occur
    """
    request_id = set_request_id()
    # Normalize tag_names for logging
    tag_list_for_log = [tag_names] if isinstance(tag_names, str) else list(tag_names)
    log.info(
        "read_timeseries_called",
        tag_names=tag_list_for_log,
        start_time=start_time,
        end_time=end_time,
        page_size=page_size,
        request_id=request_id,
        tool="read_timeseries",
    )

    try:
        # Normalize tag_names to list
        if isinstance(tag_names, str):
            tag_list = [tag_names]
        else:
            tag_list = list(tag_names)

        # Validate tag names
        if not tag_list or all(not tag.strip() for tag in tag_list):
            return {
                "success": False,
                "error": "Tag names cannot be empty",
                "data": [],
                "count": 0,
                "tag_names": tag_list,
            }

        # Parse time expressions
        try:
            parsed_start_time = parse_time_expression(start_time)
            parsed_end_time = parse_time_expression(end_time)
        except ValueError as e:
            return {
                "success": False,
                "error": f"Invalid time expression: {str(e)}",
                "data": [],
                "count": 0,
                "tag_names": tag_list,
            }

        # Validate time range
        try:
            start_dt = datetime.fromisoformat(parsed_start_time.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(parsed_end_time.replace("Z", "+00:00"))
            if start_dt >= end_dt:
                return {
                    "success": False,
                    "error": "Start time must be before end time",
                    "data": [],
                    "count": 0,
                    "tag_names": tag_list,
                    "start_time": parsed_start_time,
                    "end_time": parsed_end_time,
                }
        except (ValueError, AttributeError) as e:
            return {
                "success": False,
                "error": f"Invalid time format: {str(e)}",
                "data": [],
                "count": 0,
                "tag_names": tag_list,
            }

        # Get Canary Views base URL from environment
        views_base_url = os.getenv("CANARY_VIEWS_BASE_URL", "")
        if not views_base_url:
            raise ValueError("CANARY_VIEWS_BASE_URL not configured")

        # Authenticate and get API token
        async with CanaryAuthClient() as client:
            api_token = await client.get_valid_token()

            # Query Canary API for timeseries data
            # Using getTagData endpoint to retrieve historical data
            data_url = f"{views_base_url}/api/v2/getTagData"

            async with httpx.AsyncClient(timeout=30.0) as http_client:
                response = await http_client.post(
                    data_url,
                    json={
                        "apiToken": api_token,
                        "tags": tag_list,
                        "startTime": parsed_start_time,
                        "endTime": parsed_end_time,
                    },
                )

                response.raise_for_status()
                api_response = response.json()

                # Parse timeseries data from response
                data_points = []
                if isinstance(api_response, dict):
                    # Check if this is a "no data" vs "tag not found" scenario
                    if "data" in api_response:
                        raw_data = api_response.get("data", [])
                        for point in raw_data:
                            if isinstance(point, dict):
                                data_points.append(
                                    {
                                        "timestamp": point.get(
                                            "timestamp", point.get("time", "")
                                        ),
                                        "value": point.get("value"),
                                        "quality": point.get("quality", "Unknown"),
                                        "tagName": point.get("tagName", ""),
                                    }
                                )
                    elif "error" in api_response:
                        error_msg = api_response.get("error", "Unknown error")
                        if "not found" in error_msg.lower():
                            return {
                                "success": False,
                                "error": f"Tag not found: {error_msg}",
                                "data": [],
                                "count": 0,
                                "tag_names": tag_list,
                                "start_time": parsed_start_time,
                                "end_time": parsed_end_time,
                            }
                        return {
                            "success": False,
                            "error": error_msg,
                            "data": [],
                            "count": 0,
                            "tag_names": tag_list,
                            "start_time": parsed_start_time,
                            "end_time": parsed_end_time,
                        }

                log.info(
                    "read_timeseries_success",
                    tag_names=tag_list,
                    data_point_count=len(data_points),
                    start_time=parsed_start_time,
                    end_time=parsed_end_time,
                    request_id=get_request_id(),
                )
                return {
                    "success": True,
                    "data": data_points,
                    "count": len(data_points),
                    "tag_names": tag_list,
                    "start_time": parsed_start_time,
                    "end_time": parsed_end_time,
                }

    except CanaryAuthError as e:
        error_msg = f"Authentication failed: {str(e)}"
        log.error(
            "read_timeseries_auth_failed",
            error=error_msg,
            tag_names=tag_list if "tag_list" in locals() else [],
            request_id=get_request_id(),
        )
        return {
            "success": False,
            "error": error_msg,
            "data": [],
            "count": 0,
            "tag_names": tag_list if "tag_list" in locals() else [],
        }

    except httpx.HTTPStatusError as e:
        error_msg = (
            f"API request failed with status {e.response.status_code}: {e.response.text}"
        )
        log.error(
            "read_timeseries_api_error",
            error=error_msg,
            status_code=e.response.status_code,
            tag_names=tag_list if "tag_list" in locals() else [],
            request_id=get_request_id(),
        )
        return {
            "success": False,
            "error": error_msg,
            "data": [],
            "count": 0,
            "tag_names": tag_list if "tag_list" in locals() else [],
        }

    except httpx.RequestError as e:
        error_msg = f"Network error accessing Canary API: {str(e)}"
        log.error(
            "read_timeseries_network_error",
            error=error_msg,
            tag_names=tag_list if "tag_list" in locals() else [],
            request_id=get_request_id(),
        )
        return {
            "success": False,
            "error": error_msg,
            "data": [],
            "count": 0,
            "tag_names": tag_list if "tag_list" in locals() else [],
        }

    except Exception as e:
        error_msg = f"Unexpected error retrieving timeseries data: {str(e)}"
        log.error(
            "read_timeseries_unexpected_error",
            error=error_msg,
            tag_names=tag_list if "tag_list" in locals() else [],
            request_id=get_request_id(),
            exc_info=True,
        )
        return {
            "success": False,
            "error": error_msg,
            "data": [],
            "count": 0,
            "tag_names": tag_list if "tag_list" in locals() else [],
        }


@mcp.tool()
async def get_server_info() -> dict[str, Any]:
    """
    Get Canary server health and capability information.

    This tool retrieves server version, status, supported time zones,
    and aggregation functions from the Canary historian, along with
    MCP server configuration details.

    Returns:
        dict[str, Any]: Dictionary containing server information with keys:
            - success: Boolean indicating if operation succeeded
            - server_info: Dictionary with Canary server details
            - mcp_info: Dictionary with MCP server details
            - error: Error message (only on failure)

    Raises:
        Exception: If authentication fails or API request errors occur
    """
    request_id = set_request_id()
    log.info("get_server_info_called", request_id=request_id, tool="get_server_info")

    try:
        # Get Canary Views base URL from environment
        views_base_url = os.getenv("CANARY_VIEWS_BASE_URL", "")
        if not views_base_url:
            raise ValueError("CANARY_VIEWS_BASE_URL not configured")

        saf_base_url = os.getenv("CANARY_SAF_BASE_URL", "")

        # Authenticate and get API token
        async with CanaryAuthClient() as client:
            api_token = await client.get_valid_token()

            # Query Canary API for server capabilities
            async with httpx.AsyncClient(timeout=10.0) as http_client:
                # Get supported time zones
                timezones_url = f"{views_base_url}/api/v2/getTimeZones"
                timezones_response = await http_client.post(
                    timezones_url,
                    json={"apiToken": api_token},
                )
                timezones_response.raise_for_status()
                timezones_data = timezones_response.json()

                # Get supported aggregation functions
                aggregates_url = f"{views_base_url}/api/v2/getAggregates"
                aggregates_response = await http_client.post(
                    aggregates_url,
                    json={"apiToken": api_token},
                )
                aggregates_response.raise_for_status()
                aggregates_data = aggregates_response.json()

                # Parse server capabilities
                timezones = []
                if isinstance(timezones_data, dict):
                    timezones = timezones_data.get("timeZones", [])
                elif isinstance(timezones_data, list):
                    timezones = timezones_data

                aggregates = []
                if isinstance(aggregates_data, dict):
                    aggregates = aggregates_data.get("aggregates", [])
                elif isinstance(aggregates_data, list):
                    aggregates = aggregates_data

                # Build server info response
                server_info = {
                    "canary_server_url": views_base_url,
                    "api_version": "v2",
                    "connected": True,
                    # Limit to 10 for readability
                    "supported_timezones": (
                        timezones[:10] if len(timezones) > 10 else timezones
                    ),
                    "total_timezones": len(timezones),
                    # Limit to 10 for readability
                    "supported_aggregates": (
                        aggregates[:10] if len(aggregates) > 10 else aggregates
                    ),
                    "total_aggregates": len(aggregates),
                }

                # MCP server info
                mcp_info = {
                    "server_name": "Canary MCP Server",
                    "version": "1.0.0",  # TODO: Get from package metadata
                    "configuration": {
                        "saf_base_url": saf_base_url,
                        "views_base_url": views_base_url,
                    },
                }

                log.info(
                    "get_server_info_success",
                    canary_server_url=views_base_url,
                    api_version="v2",
                    connected=True,
                    timezone_count=len(timezones),
                    aggregate_count=len(aggregates),
                    request_id=get_request_id(),
                )
                return {
                    "success": True,
                    "server_info": server_info,
                    "mcp_info": mcp_info,
                }

    except CanaryAuthError as e:
        error_msg = f"Authentication failed: {str(e)}"
        log.error("get_server_info_auth_failed", error=error_msg, request_id=get_request_id())
        return {
            "success": False,
            "error": error_msg,
            "server_info": {},
            "mcp_info": {},
        }

    except httpx.HTTPStatusError as e:
        error_msg = (
            f"API request failed with status {e.response.status_code}: {e.response.text}"
        )
        log.error(
            "get_server_info_api_error",
            error=error_msg,
            status_code=e.response.status_code,
            request_id=get_request_id(),
        )
        return {
            "success": False,
            "error": error_msg,
            "server_info": {},
            "mcp_info": {},
        }

    except httpx.RequestError as e:
        error_msg = f"Network error accessing Canary API: {str(e)}"
        log.error("get_server_info_network_error", error=error_msg, request_id=get_request_id())
        return {
            "success": False,
            "error": error_msg,
            "server_info": {},
            "mcp_info": {},
        }

    except Exception as e:
        error_msg = f"Unexpected error retrieving server info: {str(e)}"
        log.error(
            "get_server_info_unexpected_error",
            error=error_msg,
            request_id=get_request_id(),
            exc_info=True,
        )
        return {
            "success": False,
            "error": error_msg,
            "server_info": {},
            "mcp_info": {},
        }


def main() -> None:
    """Run the MCP server."""
    import sys

    # Configure logging before starting server
    configure_logging()

    log.info("Starting Canary MCP Server", version="1.0.0")

    # Validate configuration before starting server
    # TEMPORARILY DISABLED: Uncomment when correct API endpoint is configured
    # try:
    #     asyncio.run(validate_config())
    # except Exception as e:
    #     log.error("Configuration validation failed", error=str(e))
    #     print(f"Configuration validation failed: {e}", file=sys.stderr)
    #     print(
    #         "Please check your .env file and ensure all required "
    #         "variables are set.",
    #         file=sys.stderr
    #     )
    #     return

    # Note: All print statements for MCP must go to stderr, not stdout
    # stdout is reserved for MCP JSON protocol messages
    print("Starting Canary MCP Server...", file=sys.stderr)
    print(
        "WARNING: Configuration validation disabled - "
        "server will start but API calls may fail",
        file=sys.stderr,
    )
    print(
        "         Please verify your CANARY_SAF_BASE_URL "
        "and CANARY_VIEWS_BASE_URL settings",
        file=sys.stderr,
    )

    log.info("MCP server starting", transport="stdio")
    mcp.run()
    log.info("MCP server stopped")


if __name__ == "__main__":
    main()
