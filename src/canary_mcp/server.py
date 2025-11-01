"""Main MCP server module for Canary Historian integration."""

import asyncio
import os
import re
from collections import OrderedDict
from datetime import datetime, timedelta
from typing import Any, Optional

import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP

from canary_mcp.auth import CanaryAuthError, CanaryAuthClient
from canary_mcp.cache import get_cache_store
from canary_mcp.logging_setup import configure_logging, get_logger
from canary_mcp.metrics import get_metrics_collector, MetricsTimer
from canary_mcp.request_context import set_request_id, get_request_id

# Load environment variables
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("Canary MCP Server")

# Get logger instance
log = get_logger(__name__)

# Common stop words filtered from natural language descriptions when extracting
# candidate keywords for tag lookup. These focus the search on process terms.
STOP_WORDS = {
    "the",
    "a",
    "an",
    "for",
    "and",
    "or",
    "to",
    "of",
    "in",
    "on",
    "at",
    "by",
    "from",
    "with",
    "tag",
    "tags",
    "data",
    "value",
    "values",
    "reading",
    "measure",
    "measurement",
    "sensor",
    "please",
    "show",
    "get",
    "find",
    "average",
    "mean",
    "give",
    "need",
    "looking",
    "latest",
    "current",
}


def _deduplicate_sequence(items: list[str]) -> list[str]:
    """Deduplicate a list while preserving order."""
    return list(OrderedDict.fromkeys(items))


def extract_keywords(description: str, min_length: int = 2) -> list[str]:
    """
    Extract meaningful keywords from a natural-language description.

    Args:
        description: Free-form natural language query
        min_length: Minimum word length to be considered a keyword

    Returns:
        list[str]: Ordered list of unique keywords
    """
    if not description:
        return []

    # Split on non-alphanumeric characters and lowercase tokens
    raw_tokens = re.findall(r"[A-Za-z0-9]+", description.lower())

    filtered_tokens: list[str] = []
    for token in raw_tokens:
        if len(token) < min_length:
            continue
        if token in STOP_WORDS:
            continue
        filtered_tokens.append(token)

    return _deduplicate_sequence(filtered_tokens)


def _collect_metadata_text(metadata: dict[str, Any]) -> str:
    """
    Flatten metadata dictionary into a searchable text blob.

    Args:
        metadata: Tag metadata dictionary

    Returns:
        str: Lowercase text containing string representations of metadata values
    """
    if not metadata:
        return ""

    fragments: list[str] = []

    def _walk(value: Any) -> None:
        if value is None:
            return
        if isinstance(value, str):
            fragments.append(value.lower())
        elif isinstance(value, (int, float)):
            fragments.append(str(value).lower())
        elif isinstance(value, list):
            for item in value:
                _walk(item)
        elif isinstance(value, dict):
            for nested_val in value.values():
                _walk(nested_val)

    _walk(metadata)
    return " ".join(fragments)


def _score_tag_candidate(
    keywords: list[str],
    *,
    name: str,
    path: str,
    description: str = "",
    metadata: Optional[dict[str, Any]] = None,
) -> tuple[float, dict[str, list[str]]]:
    """
    Compute a relevance score for a tag candidate against a keyword list.

    Args:
        keywords: Keywords derived from the user description
        name: Tag name
        path: Full tag path
        description: Tag description
        metadata: Additional metadata properties

    Returns:
        tuple[float, dict[str, list[str]]]: Score and keyword matches by field
    """
    if metadata is None:
        metadata = {}

    name_text = (name or "").lower()
    path_text = (path or "").lower()
    description_text = (description or "").lower()
    metadata_text = _collect_metadata_text(metadata)

    matched: dict[str, list[str]] = {
        "name": [],
        "path": [],
        "description": [],
        "metadata": [],
    }

    score = 0.0
    NAME_WEIGHT = 5.0
    PATH_WEIGHT = 3.0
    DESCRIPTION_WEIGHT = 2.0
    METADATA_WEIGHT = 1.0
    STARTS_WITH_BONUS = 1.5
    EXACT_MATCH_BONUS = 3.0

    for keyword in keywords:
        if not keyword:
            continue

        # Tag name weighting
        if keyword in name_text:
            occurrences = name_text.count(keyword)
            score += occurrences * NAME_WEIGHT
            matched["name"].append(keyword)

            if name_text.startswith(keyword):
                score += STARTS_WITH_BONUS
            if name_text == keyword:
                score += EXACT_MATCH_BONUS

        # Tag path weighting (less than name)
        if keyword in path_text:
            occurrences = path_text.count(keyword)
            score += occurrences * PATH_WEIGHT
            matched["path"].append(keyword)

        # Description weighting (lower weight)
        if keyword in description_text:
            occurrences = description_text.count(keyword)
            score += occurrences * DESCRIPTION_WEIGHT
            matched["description"].append(keyword)

        # Additional metadata weighting (lowest priority)
        if metadata_text and keyword in metadata_text:
            occurrences = metadata_text.count(keyword)
            score += occurrences * METADATA_WEIGHT
            matched["metadata"].append(keyword)

    # Deduplicate matched keyword lists
    for key in matched:
        matched[key] = _deduplicate_sequence(matched[key])

    return score, matched


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
async def search_tags(search_pattern: str, bypass_cache: bool = False) -> dict[str, Any]:
    """
    Search for Canary tags by name pattern.

    This tool searches for industrial process tags in the Canary historian
    that match the provided search pattern. Results are cached for performance.

    Args:
        search_pattern: Tag name or pattern to search for (supports wildcards)
        bypass_cache: If True, skip cache and fetch fresh data (default: False)

    Returns:
        dict[str, Any]: Dictionary containing search results with keys:
            - tags: List of matching tags with metadata
            - count: Total number of tags found
            - success: Boolean indicating if operation succeeded
            - pattern: The search pattern used
            - cached: Boolean indicating if result came from cache

    Raises:
        Exception: If authentication fails or API request errors occur
    """
    request_id = set_request_id()
    log.info(
        "search_tags_called",
        search_pattern=search_pattern,
        bypass_cache=bypass_cache,
        request_id=request_id,
        tool="search_tags",
    )

    async with MetricsTimer("search_tags") as timer:
        try:
            # Check cache first (unless bypassed)
            cache = get_cache_store()
            cache_key = cache._generate_cache_key("search", search_pattern)

            if not bypass_cache:
                cached_result = cache.get(cache_key)
                if cached_result:
                    timer.cache_hit = True
                    log.info(
                        "search_tags_cache_hit",
                        pattern=search_pattern,
                        request_id=get_request_id(),
                    )
                    cached_result["cached"] = True
                    return cached_result

            timer.cache_hit = False

            # Validate search pattern
            if not search_pattern or not search_pattern.strip():
                return {
                    "success": False,
                    "error": "Search pattern cannot be empty",
                    "tags": [],
                    "count": 0,
                    "pattern": search_pattern,
                    "cached": False,
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

                    result = {
                        "success": True,
                        "tags": tags,
                        "count": len(tags),
                        "pattern": search_pattern,
                        "cached": False,
                    }

                    # Cache the result
                    cache.set(cache_key, result, category="metadata")

                    log.info(
                        "search_tags_success",
                        pattern=search_pattern,
                        tag_count=len(tags),
                        request_id=get_request_id(),
                    )
                    return result

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
                "cached": False,
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
                "cached": False,
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
                "cached": False,
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
                "cached": False,
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


async def _get_tag_metadata_cached(
    tag_path: str,
    *,
    bypass_cache: bool,
    cache,
) -> tuple[dict[str, Any], bool]:
    """
    Retrieve tag metadata with optional caching.

    Args:
        tag_path: Full tag path to retrieve metadata for
        bypass_cache: If True, skip cache lookup
        cache: Cache store instance

    Returns:
        tuple[dict[str, Any], bool]: Metadata dictionary and cache-hit flag
    """
    cache_key = cache._generate_cache_key("tag_metadata", tag_path)

    if not bypass_cache:
        cached_metadata = cache.get(cache_key)
        if cached_metadata is not None:
            return cached_metadata, True

    metadata: dict[str, Any] = {}
    try:
        metadata_result = await get_tag_metadata.fn(tag_path)
    except Exception as exc:  # pragma: no cover - defensive logging
        log.error(
            "get_tag_path_metadata_unexpected_error",
            tag_path=tag_path,
            error=str(exc),
            request_id=get_request_id(),
            exc_info=True,
        )
        return metadata, False

    if metadata_result.get("success"):
        metadata = metadata_result.get("metadata", {}) or {}
        cache.set(cache_key, metadata, category="metadata")
    else:
        log.warning(
            "get_tag_path_metadata_failed",
            tag_path=tag_path,
            error=metadata_result.get("error"),
            request_id=get_request_id(),
        )

    return metadata, False


@mcp.tool()
async def get_tag_path(
    description: str,
    max_results: int = 5,
    bypass_cache: bool = False,
) -> dict[str, Any]:
    """
    Resolve a natural-language tag description to the best-matching tag path.

    Args:
        description: Natural-language description of the desired tag
        max_results: Maximum number of candidate tags to return
        bypass_cache: If True, skip cached results and fetch fresh data

    Returns:
        dict[str, Any]: Response containing the most likely tag path and candidates
    """
    request_id = set_request_id()
    log.info(
        "get_tag_path_called",
        description=description,
        bypass_cache=bypass_cache,
        max_results=max_results,
        request_id=request_id,
        tool="get_tag_path",
    )

    async with MetricsTimer("get_tag_path") as timer:
        cache = get_cache_store()
        description_normalized = (description or "").strip()

        # Validate input
        if not description_normalized:
            timer.cache_hit = False
            return {
                "success": False,
                "error": "Description cannot be empty",
                "description": description,
                "keywords": [],
                "most_likely_path": None,
                "candidates": [],
                "alternatives": [],
                "cached": False,
            }

        keywords = extract_keywords(description_normalized)
        if not keywords:
            timer.cache_hit = False
            return {
                "success": False,
                "error": "Unable to extract meaningful keywords from description",
                "description": description,
                "keywords": [],
                "most_likely_path": None,
                "candidates": [],
                "alternatives": [],
                "cached": False,
            }

        if max_results <= 0:
            max_results = 5

        cache_key = cache._generate_cache_key("get_tag_path", description_normalized.lower())

        if not bypass_cache:
            cached_result = cache.get(cache_key)
            if cached_result:
                timer.cache_hit = True
                cached_result["cached"] = True
                log.info(
                    "get_tag_path_cache_hit",
                    description=description_normalized,
                    keyword_count=len(keywords),
                    request_id=get_request_id(),
                )
                return cached_result

        timer.cache_hit = False

        # Determine search patterns using keywords
        search_patterns: list[str] = []
        combined_pattern = " ".join(keywords)
        if combined_pattern:
            search_patterns.append(combined_pattern)

        for keyword in keywords[:3]:
            if keyword not in search_patterns:
                search_patterns.append(keyword)

        candidate_map: dict[str, dict[str, Any]] = {}

        # Initial candidate search leveraging existing search_tags tool
        for pattern in search_patterns:
            try:
                search_result = await search_tags.fn(pattern, bypass_cache=bypass_cache)
            except Exception as exc:  # pragma: no cover - defensive logging
                log.error(
                    "get_tag_path_search_exception",
                    pattern=pattern,
                    error=str(exc),
                    request_id=get_request_id(),
                    exc_info=True,
                )
                continue

            if not search_result.get("success"):
                log.warning(
                    "get_tag_path_search_failed",
                    pattern=pattern,
                    error=search_result.get("error"),
                    request_id=get_request_id(),
                )
                continue

            for tag in search_result.get("tags", []):
                if not isinstance(tag, dict):
                    continue

                path = tag.get("path") or tag.get("name")
                if not path:
                    continue

                candidate_entry = candidate_map.setdefault(
                    path,
                    {
                        "name": tag.get("name", path.split(".")[-1]),
                        "path": path,
                        "dataType": tag.get("dataType", "unknown"),
                        "description": tag.get("description", ""),
                        "search_sources": set(),
                    },
                )
                candidate_entry["search_sources"].add(pattern)

        if not candidate_map:
            result = {
                "success": False,
                "description": description,
                "keywords": keywords,
                "error": "No tags found matching the description",
                "most_likely_path": None,
                "candidates": [],
                "alternatives": [],
                "cached": False,
            }
            cache.set(cache_key, result, category="metadata")
            log.info(
                "get_tag_path_no_candidates",
                description=description_normalized,
                keyword_count=len(keywords),
                request_id=get_request_id(),
            )
            return result

        candidate_paths = list(candidate_map.keys())
        metadata_limit = min(
            len(candidate_paths),
            max(max_results * 3, max_results),
        )
        candidate_paths = candidate_paths[:metadata_limit]

        metadata_tasks = [
            _get_tag_metadata_cached(path, bypass_cache=bypass_cache, cache=cache)
            for path in candidate_paths
        ]

        metadata_results = await asyncio.gather(*metadata_tasks, return_exceptions=True)

        candidates: list[dict[str, Any]] = []

        for path, metadata_result in zip(candidate_paths, metadata_results):
            metadata_cached = False
            metadata: dict[str, Any] = {}

            if isinstance(metadata_result, Exception):
                log.error(
                    "get_tag_path_metadata_exception",
                    tag_path=path,
                    error=str(metadata_result),
                    request_id=get_request_id(),
                    exc_info=True,
                )
            else:
                metadata, metadata_cached = metadata_result

            base_info = candidate_map[path]
            candidate_name = metadata.get("name", base_info.get("name", ""))
            candidate_description = metadata.get("description") or base_info.get("description", "")
            candidate_data_type = metadata.get("dataType", base_info.get("dataType", "unknown"))

            score, matched_keywords = _score_tag_candidate(
                keywords,
                name=candidate_name,
                path=metadata.get("path", path),
                description=candidate_description,
                metadata=metadata,
            )

            candidates.append(
                {
                    "path": metadata.get("path", path),
                    "name": candidate_name,
                    "dataType": candidate_data_type,
                    "description": candidate_description,
                    "score": round(score, 4),
                    "matched_keywords": {field: matches for field, matches in matched_keywords.items() if matches},
                    "search_sources": sorted(base_info["search_sources"]),
                    "metadata": metadata,
                    "metadata_cached": metadata_cached,
                }
            )

        # In case additional candidates were discovered but metadata not fetched
        if len(candidate_map) > len(candidates):
            for path in list(candidate_map.keys())[metadata_limit:]:
                base_info = candidate_map[path]
                score, matched_keywords = _score_tag_candidate(
                    keywords,
                    name=base_info.get("name", ""),
                    path=path,
                    description=base_info.get("description", ""),
                    metadata={},
                )
                candidates.append(
                    {
                        "path": path,
                        "name": base_info.get("name", ""),
                        "dataType": base_info.get("dataType", "unknown"),
                        "description": base_info.get("description", ""),
                        "score": round(score, 4),
                        "matched_keywords": {field: matches for field, matches in matched_keywords.items() if matches},
                        "search_sources": sorted(base_info["search_sources"]),
                        "metadata": {},
                        "metadata_cached": False,
                    }
                )

        candidates.sort(key=lambda item: item["score"], reverse=True)

        trimmed_candidates = candidates[:max_results]
        most_likely_path = trimmed_candidates[0]["path"] if trimmed_candidates else None
        alternatives = [candidate["path"] for candidate in trimmed_candidates[1:]]

        result = {
            "success": most_likely_path is not None,
            "description": description,
            "keywords": keywords,
            "most_likely_path": most_likely_path,
            "candidates": trimmed_candidates,
            "alternatives": alternatives,
            "cached": False,
        }

        cache.set(cache_key, result, category="metadata")

        log.info(
            "get_tag_path_success",
            description=description_normalized,
            keyword_count=len(keywords),
            candidate_count=len(trimmed_candidates),
            request_id=get_request_id(),
        )

        return result

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
                        "pageSize": page_size,
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


@mcp.tool()
def get_metrics() -> str:
    """
    Get performance metrics in Prometheus format.

    Story 2.1: Returns collected metrics including request counts, latencies,
    cache hit/miss rates, and connection pool statistics.

    Returns:
        str: Metrics formatted in Prometheus text exposition format

    Example:
        ```
        # HELP canary_requests_total Total number of requests by tool
        # TYPE canary_requests_total counter
        canary_requests_total{tool_name="search_tags",status_code="200"} 42
        ...
        ```
    """
    request_id = set_request_id()
    log.info("get_metrics_called", request_id=request_id, tool="get_metrics")

    try:
        collector = get_metrics_collector()
        prometheus_output = collector.export_prometheus()

        log.info(
            "get_metrics_success",
            metrics_size_bytes=len(prometheus_output),
            request_id=get_request_id(),
        )

        return prometheus_output

    except Exception as e:
        error_msg = f"Failed to export metrics: {str(e)}"
        log.error(
            "get_metrics_error",
            error=error_msg,
            request_id=get_request_id(),
            exc_info=True,
        )
        return f"# Error exporting metrics: {error_msg}\n"


@mcp.tool()
def get_metrics_summary() -> dict[str, Any]:
    """
    Get human-readable summary of performance metrics.

    Story 2.1: Returns aggregated metrics including request counts, latency percentiles,
    and cache statistics for all MCP tools.

    Returns:
        dict[str, Any]: Dictionary containing metric summaries with keys:
            - total_requests: Total number of requests processed
            - by_tool: Per-tool statistics (counts, latencies, cache stats)
            - cache_stats: Overall cache hit/miss counts
            - active_connections: Current connection pool usage

    Example:
        ```json
        {
            "total_requests": 156,
            "by_tool": {
                "search_tags": {
                    "request_count": 42,
                    "latency": {"median": 1.2, "p95": 3.5, "p99": 5.1},
                    "cache_hits": 10,
                    "cache_misses": 32
                }
            },
            "cache_stats": {"total_hits": 45, "total_misses": 111},
            "active_connections": 3
        }
        ```
    """
    request_id = set_request_id()
    log.info("get_metrics_summary_called", request_id=request_id, tool="get_metrics_summary")

    try:
        collector = get_metrics_collector()
        summary = collector.get_summary_stats()

        log.info(
            "get_metrics_summary_success",
            total_requests=summary.get("total_requests", 0),
            tools_tracked=len(summary.get("by_tool", {})),
            request_id=get_request_id(),
        )

        return {
            "success": True,
            "metrics": summary,
        }

    except Exception as e:
        error_msg = f"Failed to get metrics summary: {str(e)}"
        log.error(
            "get_metrics_summary_error",
            error=error_msg,
            request_id=get_request_id(),
            exc_info=True,
        )
        return {
            "success": False,
            "error": error_msg,
            "metrics": {},
        }


@mcp.tool()
def get_cache_stats() -> dict[str, Any]:
    """
    Get cache statistics.

    Story 2.2: Returns cache performance statistics including hit rate, size, and entry count.

    Returns:
        dict[str, Any]: Dictionary containing cache statistics with keys:
            - success: Boolean indicating if operation succeeded
            - stats: Cache statistics object

    Example:
        ```json
        {
            "success": true,
            "stats": {
                "entry_count": 42,
                "total_size_mb": 12.5,
                "max_size_mb": 100,
                "cache_hits": 150,
                "cache_misses": 30,
                "hit_rate_percent": 83.3,
                "evictions": 5
            }
        }
        ```
    """
    request_id = set_request_id()
    log.info("get_cache_stats_called", request_id=request_id, tool="get_cache_stats")

    try:
        cache = get_cache_store()
        stats = cache.get_stats()

        log.info(
            "get_cache_stats_success",
            entry_count=stats.get("entry_count", 0),
            hit_rate=stats.get("hit_rate_percent", 0),
            request_id=get_request_id(),
        )

        return {
            "success": True,
            "stats": stats,
        }

    except Exception as e:
        error_msg = f"Failed to get cache statistics: {str(e)}"
        log.error(
            "get_cache_stats_error",
            error=error_msg,
            request_id=get_request_id(),
            exc_info=True,
        )
        return {
            "success": False,
            "error": error_msg,
            "stats": {},
        }


@mcp.tool()
def invalidate_cache(pattern: str = "") -> dict[str, Any]:
    """
    Invalidate cache entries matching pattern.

    Story 2.2: Clears cached data, optionally filtering by pattern.
    Use this when configuration changes or fresh data is required.

    Args:
        pattern: SQL LIKE pattern for keys (empty string = invalidate all)

    Returns:
        dict[str, Any]: Dictionary containing invalidation results with keys:
            - success: Boolean indicating if operation succeeded
            - count: Number of entries invalidated
            - pattern: The pattern used (if any)

    Example:
        ```json
        {
            "success": true,
            "count": 15,
            "pattern": "search:%"
        }
        ```
    """
    request_id = set_request_id()
    log.info(
        "invalidate_cache_called",
        pattern=pattern or "ALL",
        request_id=request_id,
        tool="invalidate_cache",
    )

    try:
        cache = get_cache_store()

        # Invalidate matching entries
        count = cache.invalidate(pattern if pattern else None)

        log.info(
            "invalidate_cache_success",
            pattern=pattern or "ALL",
            count=count,
            request_id=get_request_id(),
        )

        return {
            "success": True,
            "count": count,
            "pattern": pattern or "ALL",
        }

    except Exception as e:
        error_msg = f"Failed to invalidate cache: {str(e)}"
        log.error(
            "invalidate_cache_error",
            error=error_msg,
            pattern=pattern,
            request_id=get_request_id(),
            exc_info=True,
        )
        return {
            "success": False,
            "error": error_msg,
            "count": 0,
        }


@mcp.tool()
def cleanup_expired_cache() -> dict[str, Any]:
    """
    Remove expired entries from cache.

    Story 2.2: Cleans up expired cache entries to free storage space.
    This is done automatically but can be triggered manually.

    Returns:
        dict[str, Any]: Dictionary containing cleanup results with keys:
            - success: Boolean indicating if operation succeeded
            - count: Number of expired entries removed

    Example:
        ```json
        {
            "success": true,
            "count": 8
        }
        ```
    """
    request_id = set_request_id()
    log.info("cleanup_expired_cache_called", request_id=request_id, tool="cleanup_expired_cache")

    try:
        cache = get_cache_store()
        count = cache.cleanup_expired()

        log.info(
            "cleanup_expired_cache_success",
            count=count,
            request_id=get_request_id(),
        )

        return {
            "success": True,
            "count": count,
        }

    except Exception as e:
        error_msg = f"Failed to cleanup expired cache: {str(e)}"
        log.error(
            "cleanup_expired_cache_error",
            error=error_msg,
            request_id=get_request_id(),
            exc_info=True,
        )
        return {
            "success": False,
            "error": error_msg,
            "count": 0,
        }


@mcp.tool()
def get_health() -> dict[str, Any]:
    """
    Get MCP server health status including circuit breaker state.

    Story 2.3: Advanced Error Handling & Retry Logic
    Exposes circuit breaker state and system health for monitoring.

    Returns:
        dict[str, Any]: Dictionary containing health status with keys:
            - status: Overall health status ("healthy", "degraded", "unhealthy")
            - timestamp: Current timestamp
            - circuit_breakers: Dictionary of circuit breaker states
            - cache_health: Cache system health information
            - metrics_summary: Performance metrics summary

    Example:
        ```json
        {
            "status": "healthy",
            "timestamp": "2025-11-01T10:00:00",
            "circuit_breakers": {
                "canary-api": {
                    "state": "closed",
                    "failure_count": 0,
                    "state_changes": 2
                }
            },
            "cache_health": {
                "operational": true,
                "entry_count": 42,
                "hit_rate_percent": 75.5
            }
        }
        ```
    """
    from datetime import datetime
    from canary_mcp.circuit_breaker import get_circuit_breaker

    request_id = set_request_id()
    log.info("get_health_called", request_id=request_id, tool="get_health")

    try:
        # Get circuit breaker states
        circuit_breakers = {}

        # Check canary-api circuit breaker (if it exists)
        try:
            canary_cb = get_circuit_breaker("canary-api")
            circuit_breakers["canary-api"] = canary_cb.get_stats()
        except Exception:
            # Circuit breaker may not exist yet
            circuit_breakers["canary-api"] = {
                "state": "closed",
                "failure_count": 0,
                "message": "Not initialized yet"
            }

        # Get cache health
        cache_health = {}
        try:
            cache = get_cache_store()
            cache_stats = cache.get_stats()

            total_accesses = cache_stats.get("total_accesses", 0)
            hit_rate = 0.0
            if total_accesses > 0:
                hits = cache_stats.get("cache_hits", 0)
                hit_rate = (hits / total_accesses) * 100

            cache_health = {
                "operational": True,
                "entry_count": cache_stats.get("entry_count", 0),
                "size_mb": cache_stats.get("total_size_mb", 0),
                "hit_rate_percent": round(hit_rate, 2),
            }
        except Exception as e:
            cache_health = {
                "operational": False,
                "error": str(e),
            }

        # Get metrics summary (lightweight)
        metrics_summary = {}
        try:
            collector = get_metrics_collector()
            stats = collector.get_summary_stats()
            metrics_summary = {
                "total_requests": stats.get("total_requests", 0),
                "active_connections": stats.get("active_connections", 0),
            }
        except Exception as e:
            metrics_summary = {
                "error": str(e),
            }

        # Determine overall health status
        status = "healthy"

        # Check if any circuit breakers are open
        for cb_name, cb_stats in circuit_breakers.items():
            if cb_stats.get("state") == "open":
                status = "unhealthy"
                break
            elif cb_stats.get("state") == "half_open":
                status = "degraded"

        # Check cache health
        if not cache_health.get("operational", False):
            if status == "healthy":
                status = "degraded"

        health_response = {
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "circuit_breakers": circuit_breakers,
            "cache_health": cache_health,
            "metrics_summary": metrics_summary,
        }

        log.info(
            "get_health_success",
            status=status,
            circuit_breaker_count=len(circuit_breakers),
            request_id=get_request_id(),
        )

        return health_response

    except Exception as e:
        error_msg = f"Failed to get health status: {str(e)}"
        log.error(
            "get_health_error",
            error=error_msg,
            request_id=get_request_id(),
            exc_info=True,
        )
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
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
