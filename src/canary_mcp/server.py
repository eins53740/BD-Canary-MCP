"""Main MCP server module for Canary Historian integration."""

import asyncio
import json
import os
import re
from collections import OrderedDict
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from textwrap import dedent
from typing import Any, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.prompts import Message

from canary_mcp.auth import CanaryAuthClient, CanaryAuthError
from canary_mcp.cache import get_cache_store
from canary_mcp.logging_setup import configure_logging, get_logger
from canary_mcp.metrics import MetricsTimer, get_metrics_collector
from canary_mcp.request_context import get_request_id, set_request_id
from canary_mcp.tag_index import get_local_tag_candidates

# Load environment variables
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP(
    "Canary MCP Server",
    instructions=(
        "Expose Canary historian metadata, guide natural-language requests toward precise tag "
        "paths, and lean on the tag catalog resource plus the tag_lookup_workflow prompt to "
        "clarify any ambiguous user intent. Interpret time ranges with the Canary relative time "
        "standard (see resource://canary/time-standards) and convert results from the "
        "Europe/Lisbon timezone to UTC. When requesting data for more than one tag, prefer the "
        "historian POST endpoints instead of multi-tag GET queries."
    ),
)

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

REPO_ROOT = Path(__file__).resolve().parents[2]
TAG_METADATA_PATH = Path(
    os.getenv(
        "CANARY_TAG_METADATA_PATH",
        REPO_ROOT / "docs" / "aux_files" / "Canary_Path_description_maceira.json",
    )
)
TAG_NOTES_PATH = Path(
    os.getenv(
        "CANARY_TAG_NOTES_PATH",
        REPO_ROOT / "docs" / "aux_files" / "maceira_postman_exampes.txt",
    )
)
DEFAULT_TIMEZONE = os.getenv("CANARY_TIMEZONE", "Europe/Lisbon")
try:
    DEFAULT_TZINFO = ZoneInfo(DEFAULT_TIMEZONE)
except ZoneInfoNotFoundError:
    DEFAULT_TZINFO = UTC

SEARCH_TAGS_HINT = (
    "Describe the process area and distinctive identifiers (e.g. 'Maceira kiln shell temperature "
    "P431'). Prefer exact fragments over wildcards; combine with resource://canary/tag-catalog to "
    "confirm descriptions and units."
)
DEFAULT_SEARCH_PATH_FALLBACKS = ("Secil.Portugal",)
NORMALIZED_PROPERTY_KEY_ALIASES = {
    "name": ("name", "tagname", "tag"),
    "path": ("path", "tagpath", "source itemid", "historian itemid"),
    "dataType": ("datatype", "type", "datatypeid"),
    "description": ("description", "documentation"),
    "units": ("units", "unit", "engineeringunits", "engunit", "engunits"),
    "engHigh": ("enghigh", "defaulthighscale"),
    "engLow": ("englow", "defaultlowscale"),
    "minValue": ("minvalue", "min"),
    "maxValue": ("maxvalue", "max"),
    "updateRate": ("updaterate", "scanrate"),
}

RELATIVE_TIME_GUIDE = dedent(
    """\
    Relative Times
    Descriptions of relative time units and how they can be used
    Usage
    DateTime
    Use relative units to represent a date/time. Example: Now - 1Month + 3Days
    TimeSpan
    Use relative units to represent a timespan. Example: 8Hours + 30Minutes + 15Seconds
    Units
    Now
    Use this to represent the current date/time
    Year
    Use this to represent the current year or to add/subtract years
    Month
    Use this to represent the start of the current month or to add/subtract months
    Week
    Use this to represent the start of the current week (Sunday) or to add/subtract weeks
    Day
    Use this to represent the start of the current day or to add/subtract days
    Hour
    Use this to represent the start of the current hour or to add/subtract hours
    Minute
    Use this to represent the start of the current minute or to add/subtract minutes
    Second
    Use this to represent the start of the current second or to add/subtract seconds
    Millisecond
    Use this to add/subtract milliseconds
    Beginning
    Use this to represent the minimum date/time value
    Ending
    Use this to represent the maximum date/time value
    DateTime Examples
    Minute - 30Minutes
    A date/time 30 minutes before the start of the current minute
    Day - 1Week
    7 days previous to the start of the current day
    Week - 4Hours
    4 hours previous to the start of the current week (Sunday)
    Hour
    Start of the current hour
    TimeSpan Examples
    4Hours + 30Minutes
    4 hours and 30 minutes
    1Week
    7 days
    90Seconds
    1 minute and 30 seconds
    """
)


def _parse_iso_timestamp(value: Any) -> Optional[datetime]:
    """Parse ISO timestamps while handling Z suffix and fractional seconds."""
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(cleaned)
    except ValueError:
        return None


def _isoformat_utc(dt: datetime) -> str:
    """Format a datetime as UTC ISO string with trailing Z."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=DEFAULT_TZINFO)
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")


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


def _normalize_property_dict(raw_properties: dict[str, Any]) -> dict[str, Any]:
    """Normalize property keys returned by Canary into a consistent metadata dict."""
    if not isinstance(raw_properties, dict):
        return {}

    normalized_keys: dict[str, Any] = {}
    for key, value in raw_properties.items():
        if not isinstance(key, str):
            continue
        alias_key = key.lower().replace(" ", "").replace("_", "")
        normalized_keys[alias_key] = value

    metadata: dict[str, Any] = {}
    for field, aliases in NORMALIZED_PROPERTY_KEY_ALIASES.items():
        for alias in aliases:
            lookup = alias.lower().replace(" ", "").replace("_", "")
            if lookup in normalized_keys:
                metadata[field] = normalized_keys[lookup]
                break

    # If 'name' is not set but 'description' is available and looks like a name, use it
    if not metadata.get("name") and metadata.get("description"):
        desc = metadata.get("description", "")
        if desc and len(desc) < 100:  # Short descriptions might be names
            metadata["name"] = desc

    # Ensure required fields exist even if empty
    metadata.setdefault("name", "")
    metadata.setdefault("path", "")
    metadata.setdefault("dataType", "unknown")
    metadata.setdefault("description", "")
    metadata.setdefault("units", "")

    return metadata


@lru_cache(maxsize=1)
def _load_tag_catalog() -> list[dict[str, Any]]:
    """Load curated tag metadata from the auxiliary Canary catalog."""
    try:
        raw_text = TAG_METADATA_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        log.warning(
            "tag_catalog_missing",
            path=str(TAG_METADATA_PATH),
        )
        return []
    except OSError as exc:
        log.error(
            "tag_catalog_unreadable",
            path=str(TAG_METADATA_PATH),
            error=str(exc),
        )
        return []

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        log.error(
            "tag_catalog_invalid_json",
            path=str(TAG_METADATA_PATH),
            error=str(exc),
        )
        return []

    catalog: list[dict[str, Any]] = []

    def _append_entry(entry: dict[str, Any]) -> None:
        path = str(entry.get("path", "")).strip()
        if not path:
            return
        catalog.append(
            {
                "path": path,
                "description": entry.get("description", "").strip(),
                "unit": entry.get("unit", "").strip(),
                "keywords": entry.get("keywords", []),
                "plant": entry.get("plant", "").strip(),
                "equipment": entry.get("equipment", "").strip(),
            }
        )

    if isinstance(payload, list):
        for block in payload:
            if isinstance(block, dict) and isinstance(block.get("tags"), list):
                for tag_entry in block["tags"]:
                    if isinstance(tag_entry, dict):
                        _append_entry(tag_entry)

    # Deduplicate by path while preserving order
    deduped: dict[str, dict[str, Any]] = OrderedDict()
    for entry in catalog:
        deduped.setdefault(entry["path"], entry)

    return list(deduped.values())


@lru_cache(maxsize=1)
def _load_tag_examples() -> list[str]:
    """Load plain-text request/response examples to assist LLM disambiguation."""
    try:
        raw_text = TAG_NOTES_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        log.warning("tag_notes_missing", path=str(TAG_NOTES_PATH))
        return []
    except OSError as exc:
        log.error("tag_notes_unreadable", path=str(TAG_NOTES_PATH), error=str(exc))
        return []

    examples: list[str] = []
    for line in raw_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("{{APIURL}}"):
            examples.append(stripped)
    return examples


def _build_asset_catalog() -> dict[str, Any]:
    """Build the structured payload exposed via the catalog resource/tool."""
    tags = _load_tag_catalog()
    examples = _load_tag_examples()
    return {
        "site": "Maceira",
        "default_timezone": DEFAULT_TIMEZONE,
        "total_tags": len(tags),
        "tags": tags,
        "examples": examples,
        "source_files": {
            "metadata": str(TAG_METADATA_PATH),
            "examples": str(TAG_NOTES_PATH),
        },
    }


def _parse_canary_timeseries_payload(
    api_response: Any,
) -> tuple[list[dict[str, Any]], Optional[Any]]:
    """Extract timeseries samples from the Canary API response structure."""
    data_points: list[dict[str, Any]] = []
    continuation = None

    if not isinstance(api_response, dict):
        return data_points, continuation

    continuation = api_response.get("continuation")
    data_section = api_response.get("data")

    def _extract_samples(tag_name: str, samples: Any) -> None:
        if not isinstance(samples, list):
            return
        for sample in samples:
            if not isinstance(sample, dict):
                continue
            timestamp = sample.get("timestamp") or sample.get("time") or sample.get("t")
            value = sample.get("value")
            if value is None and "v" in sample:
                value = sample.get("v")
            quality = sample.get("quality", sample.get("q", "Unknown"))
            data_points.append(
                {
                    "timestamp": timestamp,
                    "value": value,
                    "quality": quality,
                    "tagName": sample.get("tagName", tag_name),
                }
            )

    if isinstance(data_section, dict):
        for tag_name, samples in data_section.items():
            _extract_samples(tag_name, samples)
    elif isinstance(data_section, list):
        for sample in data_section:
            if not isinstance(sample, dict):
                continue
            tag_name = sample.get("tagName", "")
            _extract_samples(tag_name, [sample])

    return data_points, continuation


async def _resolve_tag_identifiers(
    tag_identifiers: list[str],
    *,
    include_original: bool = True,
) -> tuple[list[str], dict[str, str]]:
    """
    Expand shorthand tag identifiers into fully qualified paths using search_tags.

    Returns:
        tuple[list[str], dict[str, str]]: (lookup_paths, resolved_map)
    """
    lookup_paths: list[str] = []
    resolved_map: dict[str, str] = {}

    for identifier in tag_identifiers:
        if not identifier:
            continue
        cleaned = identifier.strip()
        if not cleaned:
            continue

        resolved_map.setdefault(cleaned, cleaned)

        if include_original and cleaned not in lookup_paths:
            lookup_paths.append(cleaned)

        if "." in cleaned:
            continue

        try:
            search_result = await search_tags.fn(cleaned, bypass_cache=False)
        except Exception as exc:  # pragma: no cover - defensive fallback
            log.warning(
                "resolve_tag_identifiers_search_error",
                identifier=cleaned,
                error=str(exc),
                request_id=get_request_id(),
            )
            continue

        for tag in search_result.get("tags", []):
            if not isinstance(tag, dict):
                continue
            path = tag.get("path") or tag.get("name")
            if not path:
                continue
            if path not in lookup_paths:
                lookup_paths.append(path)
            resolved_map[cleaned] = path
            break

    return lookup_paths, resolved_map


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
    - relative time expressions like "now-1d"

    Natural language expressions are interpreted using the configured
    CANARY_TIMEZONE (defaults to Europe/Lisbon) before being converted to UTC.

    Args:
        time_expr: Natural language time expression or ISO timestamp

    Returns:
        str: ISO timestamp string or the original expression if it's relative

    Raises:
        ValueError: If expression cannot be parsed
    """
    time_expr_lower = time_expr.lower().strip()
    now = datetime.now(DEFAULT_TZINFO)

    # Pass through relative time expressions
    if "now-" in time_expr_lower:
        return time_expr

    # Natural language expressions
    if time_expr_lower == "yesterday":
        target = now - timedelta(days=1)
        start_of_day = target.replace(hour=0, minute=0, second=0, microsecond=0)
        return _isoformat_utc(start_of_day)

    if "last week" in time_expr_lower or "past week" in time_expr_lower:
        target = now - timedelta(days=7)
        return _isoformat_utc(target)

    if "past 24 hours" in time_expr_lower or "last 24 hours" in time_expr_lower:
        target = now - timedelta(hours=24)
        return _isoformat_utc(target)

    if "last 30 days" in time_expr_lower or "past 30 days" in time_expr_lower:
        target = now - timedelta(days=30)
        return _isoformat_utc(target)

    if "last 7 days" in time_expr_lower or "past 7 days" in time_expr_lower:
        target = now - timedelta(days=7)
        return _isoformat_utc(target)

    if time_expr_lower == "now":
        return _isoformat_utc(now)

    # Try parsing as ISO timestamp as a fallback
    try:
        datetime.fromisoformat(time_expr.replace("Z", "+00:00"))
        return time_expr  # Already ISO format
    except (ValueError, AttributeError):
        pass

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


@mcp.resource(
    "resource://canary/tag-catalog",
    title="Maceira Tag Catalog",
    description=(
        "Structured metadata for the Secil Maceira site, including tag paths, descriptions, "
        "and engineering units gathered from Canary auxiliary files."
    ),
    mime_type="application/json",
    tags={"metadata", "catalog"},
)
def maceira_tag_catalog() -> dict[str, Any]:
    """Expose the curated tag catalog as an MCP resource."""
    return _build_asset_catalog()


@mcp.resource(
    "resource://canary/time-standards",
    title="Canary Relative Time Standards",
    description=(
        "Reference guide for Canary relative time expressions and Europe/Lisbon timezone defaults "
        "used in historian queries."
    ),
    mime_type="application/json",
    tags={"metadata", "time"},
)
def canary_time_standards() -> dict[str, Any]:
    """Expose the relative time guidance and default timezone for MCP clients."""
    return {
        "default_timezone": DEFAULT_TIMEZONE,
        "timezone_note": (
            f"Interpret natural-language expressions in {DEFAULT_TIMEZONE} before converting to UTC."
        ),
        "relative_time_reference": RELATIVE_TIME_GUIDE,
        "examples": [
            "DateTime: Now - 1Month + 3Days",
            "TimeSpan: 4Hours + 30Minutes + 15Seconds",
            "Minute - 30Minutes",
            "Day - 1Week",
            "Week - 4Hours",
        ],
    }


@mcp.tool()
def get_asset_catalog(
    refresh: bool = False,
    limit: int = 200,
    include_examples: bool = False,
) -> dict[str, Any]:
    """
    Retrieve curated metadata for Secil Maceira sensors, devices, and historian tags.

    This tool compiles information from the Canary auxiliary catalog so LLM or MCP clients
    can convert natural-language requests into concrete historian paths. Pair this with
    the `tag_lookup_workflow` prompt and the `search_tags` tool when the user provides only
    a partial description.

    Args:
        refresh: When True, reload the auxiliary files from disk (default: False)
        limit: Maximum number of tag entries to return inline (default: 200)
        include_examples: When True, include the raw request examples from the source file

    Returns:
        dict[str, Any]: Keys include
            - success: Whether metadata was loaded
            - tags: Inline sample of tag entries limited by ``limit``
            - examples: Optional example list (present when include_examples=True)
            - total_tags: Number of tag entries available in the catalog
            - summary: Metadata about the returned sample (site, counts, truncation)
            - resource_uri: The canonical MCP resource URI for the catalog
            - refreshed: Whether the cache was refreshed this call
            - hint: Guidance for follow-up actions
    """
    request_id = set_request_id()
    log.info(
        "get_asset_catalog_called",
        refresh=refresh,
        limit=limit,
        include_examples=include_examples,
        request_id=request_id,
    )

    if refresh:
        _load_tag_catalog.cache_clear()
        _load_tag_examples.cache_clear()

    catalog = _build_asset_catalog()
    success = bool(catalog.get("tags"))

    tags: list[dict[str, Any]] = list(catalog.get("tags", []))
    total_tags = len(tags)

    safe_limit = max(0, min(limit, 1000))  # Hard cap to avoid oversized payloads
    truncated = total_tags > safe_limit >= 0
    tags_slice = tags[:safe_limit] if safe_limit else []

    examples: list[str] = catalog.get("examples", []) if include_examples else []
    if include_examples and examples:
        # Guard against excessively large example payloads by trimming to 25 entries
        examples = examples[:25]

    log.info(
        "get_asset_catalog_completed",
        success=success,
        tag_count=total_tags,
        returned=len(tags_slice),
        truncated=truncated,
        request_id=get_request_id(),
    )
    return {
        "success": success,
        "tags": tags_slice,
        "examples": examples,
        "total_tags": total_tags,
        "summary": {
            "site": catalog.get("site"),
            "default_timezone": catalog.get("default_timezone"),
            "returned": len(tags_slice),
            "total": total_tags,
            "limit": safe_limit,
            "truncated": truncated,
        },
        "resource_uri": "resource://canary/tag-catalog",
        "refreshed": refresh,
        "hint": (
            SEARCH_TAGS_HINT
            + (
                " Call read_resource('resource://canary/tag-catalog') for the full catalog."
                if truncated
                else ""
            )
        ),
    }


@mcp.prompt(
    "tag_lookup_workflow",
    description=(
        "Workflow for translating natural-language requests into precise Canary tag paths."
    ),
    tags={"workflow", "metadata"},
)
def tag_lookup_workflow() -> list[Message]:
    """
    Step-by-step workflow guiding an LLM to resolve user requests into historian tag paths.
    """
    return [
        Message(
            role="system",
            content=(
                "You help operators navigate the Canary historian. Default to the "
                f"{DEFAULT_TIMEZONE} timezone and prefer the Secil Maceira namespace."
            ),
        ),
        Message(
            role="user",
            content=(
                "Follow this workflow:\n"
                "1. Clarify the process area, equipment, and any identifiers in the request.\n"
                "2. Check `resource://canary/tag-catalog` via `get_asset_catalog` for an exact "
                "match on description or unit.\n"
                "3. When no match is found, call `search_tags` with the strongest keyword "
                "(avoid wildcards) and review returned paths.\n"
                "4. Confirm engineering units and descriptions with `get_tag_properties` if "
                "available before recommending a path.\n"
                "5. Return the fully qualified historian path(s) and highlight confidence or "
                "follow-up checks the user should perform."
            ),
        ),
    ]


@mcp.prompt(
    "timeseries_query_workflow",
    description="Workflow for retrieving historical samples from the Canary historian.",
    tags={"workflow", "timeseries"},
)
def timeseries_query_workflow() -> list[Message]:
    """Workflow prompting for safe historical data retrieval."""
    return [
        Message(
            role="system",
            content=(
                "Assist with querying historical data while respecting Canary API constraints "
                f"and the default {DEFAULT_TIMEZONE} timezone."
            ),
        ),
        Message(
            role="user",
            content=(
                "1. Resolve tag paths using the tag lookup workflow first.\n"
                "2. Define start and end times using the Canary relative time grammar (see "
                "`resource://canary/time-standards`); interpret expressions in "
                f"{DEFAULT_TIMEZONE} before converting to UTC.\n"
                "3. Call `read_timeseries` with ISO timestamps and moderate page_size (<=1000). "
                "When retrieving more than one tag, use the historian POST endpoints instead of "
                "multi-tag GET requests.\n"
                "4. Inspect the response for continuation tokens and iterate if needed.\n"
                "5. Summarise the retrieved data, noting gaps or quality issues."
            ),
        ),
    ]


@mcp.tool()
async def search_tags(
    search_pattern: str,
    bypass_cache: bool = False,
    search_path: str | None = None,
) -> dict[str, Any]:
    """
    Search for Canary tags by name pattern.

    This tool searches for industrial process tags in the Canary historian
    that match the provided search pattern. Results are cached for performance.

    Hint: combine this tool with the `tag_lookup_workflow` prompt and the
    `resource://canary/tag-catalog` metadata. Start from literal identifiers
    (for example "P431") without introducing wildcards—Canary performs its own
    fuzzy matching and rewards precise fragments.

    Args:
        search_pattern: Tag name or pattern to search for (supports wildcards)
        bypass_cache: If True, skip cache and fetch fresh data (default: False)
        search_path: Optional namespace path to scope the browseTags query.
            Defaults to the CANARY_TAG_SEARCH_ROOT environment variable when omitted.

    Returns:
        dict[str, Any]: Dictionary containing search results with keys:
            - tags: List of matching tags with metadata
            - count: Total number of tags found
            - success: Boolean indicating if operation succeeded
            - pattern: The search pattern used
            - search_path: The path used to scope the search (may be empty)
            - cached: Boolean indicating if result came from cache

    Raises:
        Exception: If authentication fails or API request errors occur
    """
    request_id = set_request_id()

    configured_search_path = os.getenv("CANARY_TAG_SEARCH_ROOT", "").strip()
    fallback_paths_env = os.getenv("CANARY_TAG_SEARCH_FALLBACKS", "")

    raw_fallbacks = [p.strip() for p in fallback_paths_env.split(",") if p.strip()]
    explicitly_provided = search_path is not None

    candidate_paths: list[str] = []

    def _add_path(path: str | None) -> None:
        if path is None:
            return
        trimmed = path.strip()
        if trimmed not in candidate_paths:
            candidate_paths.append(trimmed)

    if explicitly_provided:
        _add_path(search_path)
    else:
        _add_path(search_path)
        _add_path(configured_search_path)
        for path in raw_fallbacks:
            _add_path(path)
        for path in DEFAULT_SEARCH_PATH_FALLBACKS:
            _add_path(path)
        _add_path("")  # Allow global search as final fallback

    # Ensure non-empty paths are attempted first for automatic fallback
    non_empty_paths = [path for path in candidate_paths if path]
    empty_present = "" in candidate_paths
    effective_paths = non_empty_paths + ([""] if empty_present else [])

    # If the caller explicitly provided a search_path (including empty string),
    # respect it and ignore automatic fallbacks.
    if explicitly_provided:
        effective_paths = [(search_path or "").strip()]

    primary_search_path = effective_paths[0] if effective_paths else ""

    log.info(
        "search_tags_called",
        search_pattern=search_pattern,
        bypass_cache=bypass_cache,
        search_paths=effective_paths,
        request_id=request_id,
        tool="search_tags",
    )

    async with MetricsTimer("search_tags") as timer:
        try:
            cache = get_cache_store()
            timer.cache_hit = False

            # Validate search pattern
            if not search_pattern or not search_pattern.strip():
                return {
                    "success": False,
                    "error": "Search pattern cannot be empty",
                    "tags": [],
                    "count": 0,
                    "pattern": search_pattern,
                    "search_path": primary_search_path,
                    "cached": False,
                    "hint": SEARCH_TAGS_HINT,
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

                fallback_result: Optional[dict[str, Any]] = None

                for path_option in effective_paths or [""]:
                    cache_key = cache._generate_cache_key(
                        "search",
                        f"{path_option}::{search_pattern}",
                    )

                    if not bypass_cache:
                        cached_result = cache.get(cache_key)
                        if cached_result:
                            timer.cache_hit = True
                            if "hint" not in cached_result:
                                cached_result["hint"] = SEARCH_TAGS_HINT
                            log.info(
                                "search_tags_cache_hit",
                                pattern=search_pattern,
                                search_path=path_option,
                                request_id=get_request_id(),
                            )
                            cached_result["cached"] = True
                            return cached_result

                    payload = {
                        "apiToken": api_token,
                        "search": search_pattern,
                        "deep": True,
                        "path": path_option,
                    }

                    async with httpx.AsyncClient(timeout=10.0) as http_client:
                        response = await http_client.post(
                            search_url,
                            json=payload,
                        )

                        response.raise_for_status()
                        data = response.json()

                    tags: list[dict[str, Any]] = []
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
                        "search_path": path_option,
                        "cached": False,
                        "hint": SEARCH_TAGS_HINT,
                    }

                    if tags:
                        cache.set(cache_key, result, category="metadata")
                        log.info(
                            "search_tags_success",
                            pattern=search_pattern,
                            tag_count=len(tags),
                            search_path=path_option,
                            request_id=get_request_id(),
                        )
                        return result

                    if fallback_result is None:
                        fallback_result = result

                if fallback_result is not None:
                    log.info(
                        "search_tags_no_results",
                        pattern=search_pattern,
                        search_paths=effective_paths,
                        request_id=get_request_id(),
                    )
                    return fallback_result

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
                "search_path": primary_search_path,
                "cached": False,
                "hint": SEARCH_TAGS_HINT,
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
                "search_path": primary_search_path,
                "cached": False,
                "hint": SEARCH_TAGS_HINT,
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
                "search_path": primary_search_path,
                "cached": False,
                "hint": SEARCH_TAGS_HINT,
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
                "search_path": primary_search_path,
                "cached": False,
                "hint": SEARCH_TAGS_HINT,
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

        # Resolve potential shorthand identifiers (e.g. P431 -> full path)
        lookup_paths, resolved_map = await _resolve_tag_identifiers([tag_path])
        if not lookup_paths:
            return {
                "success": False,
                "error": "Unable to resolve tag identifier",
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

            metadata_url = f"{views_base_url}/api/v2/getTagProperties"

            async with httpx.AsyncClient(timeout=10.0) as http_client:
                response = await http_client.post(
                    metadata_url,
                    json={
                        "apiToken": api_token,
                        "tags": lookup_paths,
                    },
                )

                response.raise_for_status()
                data = response.json()

        properties_block = {}
        if isinstance(data, dict):
            props = data.get("properties")
            if isinstance(props, dict):
                properties_block = props

        metadata: dict[str, Any] = {}
        resolved_path = resolved_map.get(tag_path.strip(), tag_path)
        for candidate in lookup_paths:
            candidate_properties = properties_block.get(candidate)
            if isinstance(candidate_properties, dict):
                normalized = _normalize_property_dict(candidate_properties)
                normalized["path"] = normalized.get("path") or candidate
                normalized["name"] = normalized.get("name") or candidate.split(".")[-1]
                normalized["properties"] = candidate_properties
                metadata = normalized
                resolved_path = candidate
                break

        if not metadata and isinstance(data, dict):
            fallback_normalized = _normalize_property_dict(data)
            if fallback_normalized:
                fallback_normalized["path"] = fallback_normalized.get("path") or resolved_path
                fallback_normalized["name"] = (
                    fallback_normalized.get("name") or resolved_path.split(".")[-1]
                )
                if isinstance(data.get("properties"), dict):
                    fallback_normalized["properties"] = data["properties"]
                metadata = fallback_normalized

        if not metadata:
            log.warning(
                "get_tag_metadata_not_found",
                tag_path=tag_path,
                resolved_candidates=lookup_paths,
                request_id=get_request_id(),
            )
            return {
                "success": False,
                "error": f"Tag metadata not found for '{tag_path}'",
                "metadata": {},
                "tag_path": tag_path,
                "resolved_path": resolved_path,
            }

        log.info(
            "get_tag_metadata_success",
            tag_path=tag_path,
            resolved_path=resolved_path,
            data_type=metadata.get("dataType"),
            units=metadata.get("units"),
            request_id=get_request_id(),
        )
        return {
            "success": True,
            "metadata": metadata,
            "tag_path": tag_path,
            "resolved_path": resolved_path,
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
        error_msg = f"API request failed with status {e.response.status_code}: {e.response.text}"
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

                if not candidate_entry.get("description") and tag.get("description"):
                    candidate_entry["description"] = tag.get("description", "")

        if not candidate_map:
            local_candidates = get_local_tag_candidates(
                keywords,
                description=description_normalized,
                limit=max_results * 6,
            )

            for candidate in local_candidates:
                path = candidate.get("path")
                if not path:
                    continue

                candidate_entry = candidate_map.setdefault(
                    path,
                    {
                        "name": candidate.get("name", path.split(".")[-1]),
                        "path": path,
                        "dataType": candidate.get("dataType", "unknown"),
                        "description": candidate.get("description", ""),
                        "search_sources": set(),
                    },
                )
                candidate_entry["search_sources"].add("local-index")

                local_metadata = candidate.get("metadata") or {}
                if local_metadata:
                    candidate_entry["local_metadata"] = {**local_metadata}

                matched_tokens = candidate.get("matched_tokens") or []
                if matched_tokens:
                    local_keywords = candidate_entry.setdefault("local_keywords", set())
                    local_keywords.update(matched_tokens)

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
            local_metadata = base_info.get("local_metadata") or {}
            combined_metadata: dict[str, Any] = {}
            combined_metadata.update(local_metadata)
            combined_metadata.update(metadata or {})

            candidate_name = combined_metadata.get("name", base_info.get("name", ""))
            candidate_description = combined_metadata.get("description") or base_info.get(
                "description", ""
            )
            candidate_data_type = combined_metadata.get(
                "dataType", base_info.get("dataType", "unknown")
            )

            metadata_path = combined_metadata.get("path", path)
            if not combined_metadata.get("path"):
                combined_metadata["path"] = metadata_path

            score, matched_keywords = _score_tag_candidate(
                keywords,
                name=candidate_name,
                path=metadata_path,
                description=candidate_description,
                metadata=combined_metadata,
            )

            local_keywords = base_info.get("local_keywords")
            if local_keywords:
                matched_keywords["local_index"] = _deduplicate_sequence(sorted(local_keywords))

            candidates.append(
                {
                    "path": metadata_path,
                    "name": candidate_name,
                    "dataType": candidate_data_type,
                    "description": candidate_description,
                    "score": round(score, 4),
                    "matched_keywords": {
                        field: matches for field, matches in matched_keywords.items() if matches
                    },
                    "search_sources": sorted(base_info["search_sources"]),
                    "metadata": combined_metadata,
                    "metadata_cached": metadata_cached,
                }
            )

        # In case additional candidates were discovered but metadata not fetched
        if len(candidate_map) > len(candidates):
            for path in list(candidate_map.keys())[metadata_limit:]:
                base_info = candidate_map[path]
                local_metadata = base_info.get("local_metadata") or {}
                score, matched_keywords = _score_tag_candidate(
                    keywords,
                    name=base_info.get("name", ""),
                    path=path,
                    description=base_info.get("description", ""),
                    metadata=local_metadata,
                )
                local_keywords = base_info.get("local_keywords")
                if local_keywords:
                    matched_keywords["local_index"] = _deduplicate_sequence(sorted(local_keywords))
                candidates.append(
                    {
                        "path": path,
                        "name": base_info.get("name", ""),
                        "dataType": base_info.get("dataType", "unknown"),
                        "description": base_info.get("description", ""),
                        "score": round(score, 4),
                        "matched_keywords": {
                            field: matches for field, matches in matched_keywords.items() if matches
                        },
                        "search_sources": sorted(base_info["search_sources"]),
                        "metadata": local_metadata,
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
async def get_tag_properties(tag_paths: list[str]) -> dict[str, Any]:
    """
    Fetch raw tag property dictionaries from Canary getTagProperties API.

    Args:
        tag_paths: List of fully qualified tag paths to fetch properties for.

    Returns:
        dict[str, Any]: {
            "success": bool,
            "properties": mapping of tag path -> property dict,
            "count": number of property payloads returned,
            "requested": original tag_paths,
            "cached": always False
        }
    """
    request_id = set_request_id()
    log.info(
        "get_tag_properties_called",
        requested_tags=tag_paths,
        request_id=request_id,
        tool="get_tag_properties",
    )

    if not tag_paths or not [path for path in tag_paths if path and path.strip()]:
        return {
            "success": False,
            "error": "At least one non-empty tag path is required",
            "properties": {},
            "count": 0,
            "requested": tag_paths,
        }

    # Deduplicate and normalize paths while preserving order
    normalized_inputs: list[str] = []
    seen = set()
    for raw_path in tag_paths:
        if not raw_path:
            continue
        cleaned = raw_path.strip()
        if not cleaned or cleaned in seen:
            continue
        normalized_inputs.append(cleaned)
        seen.add(cleaned)

    if not normalized_inputs:
        return {
            "success": False,
            "error": "Tag paths must be non-empty strings",
            "properties": {},
            "count": 0,
            "requested": tag_paths,
        }

    # Resolve identifiers to fully-qualified paths only; exclude original shorthands
    lookup_paths, resolved_map = await _resolve_tag_identifiers(
        normalized_inputs, include_original=False
    )
    if not lookup_paths:
        return {
            "success": False,
            "error": "Unable to resolve tag identifiers",
            "properties": {},
            "count": 0,
            "requested": tag_paths,
        }

    try:
        views_base_url = os.getenv("CANARY_VIEWS_BASE_URL", "")
        if not views_base_url:
            raise ValueError("CANARY_VIEWS_BASE_URL not configured")

        async with CanaryAuthClient() as client:
            api_token = await client.get_valid_token()

            payload = {
                "apiToken": api_token,
                "tags": lookup_paths,
            }
            properties_url = f"{views_base_url}/api/v2/getTagProperties"

            async with httpx.AsyncClient(timeout=10.0) as http_client:
                response = await http_client.post(properties_url, json=payload)
                response.raise_for_status()
                data = response.json()

        properties: dict[str, Any] = {}

        if isinstance(data, dict):
            props_block = data.get("properties")
            if isinstance(props_block, dict):
                for path, prop in props_block.items():
                    if isinstance(prop, dict):
                        properties[path] = prop

        resolved_paths = resolved_map

        result = {
            "success": True,
            "requested": normalized_inputs,
            "properties": properties,
            "count": len(properties),
            "cached": False,
            "resolved_paths": resolved_paths,
        }

        log.info(
            "get_tag_properties_success",
            requested=len(normalized_inputs),
            returned=len(properties),
            request_id=get_request_id(),
        )

        return result

    except CanaryAuthError as exc:
        error_msg = f"Authentication failed: {exc}"
        log.error(
            "get_tag_properties_auth_failed",
            error=error_msg,
            request_id=get_request_id(),
        )
        return {
            "success": False,
            "error": error_msg,
            "properties": {},
            "count": 0,
            "requested": normalized_inputs,
        }

    except httpx.HTTPStatusError as exc:
        error_msg = (
            f"API request failed with status {exc.response.status_code}: {exc.response.text}"
        )
        log.error(
            "get_tag_properties_api_error",
            error=error_msg,
            status_code=exc.response.status_code,
            request_id=get_request_id(),
        )
        return {
            "success": False,
            "error": error_msg,
            "properties": {},
            "count": 0,
            "requested": normalized_inputs,
        }

    except httpx.RequestError as exc:
        error_msg = f"Network error accessing Canary API: {exc}"
        log.error(
            "get_tag_properties_network_error",
            error=error_msg,
            request_id=get_request_id(),
        )
        return {
            "success": False,
            "error": error_msg,
            "properties": {},
            "count": 0,
            "requested": normalized_inputs,
        }

    except Exception as exc:
        error_msg = f"Unexpected error retrieving tag properties: {exc}"
        log.error(
            "get_tag_properties_unexpected_error",
            error=error_msg,
            request_id=get_request_id(),
            exc_info=True,
        )
        return {
            "success": False,
            "error": error_msg,
            "properties": {},
            "count": 0,
            "requested": normalized_inputs,
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

                structured_nodes: list[dict[str, Any]] = []
                if isinstance(data, dict):
                    nodes = data.get("nodes")
                    if isinstance(nodes, dict):
                        for name, node in nodes.items():
                            if isinstance(node, dict):
                                structured_nodes.append(
                                    {
                                        "name": name,
                                        "path": node.get("fullPath", node.get("path", name)),
                                        "hasNodes": node.get("hasNodes", False),
                                        "hasTags": node.get("hasTags", False),
                                    }
                                )
                    elif isinstance(nodes, list):
                        for node in nodes:
                            if isinstance(node, dict):
                                structured_nodes.append(
                                    {
                                        "name": node.get("name", node.get("path")),
                                        "path": node.get("path", node.get("fullPath")),
                                        "hasNodes": node.get("hasNodes", False),
                                        "hasTags": node.get("hasTags", False),
                                    }
                                )

                namespaces = [entry.get("path") for entry in structured_nodes if entry.get("path")]

                log.info(
                    "list_namespaces_success",
                    namespace_count=len(namespaces),
                    request_id=get_request_id(),
                )
                return {
                    "success": True,
                    "namespaces": namespaces,
                    "count": len(namespaces),
                    "nodes": structured_nodes,
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
async def get_last_known_values(
    tag_names: str | list[str], views: Optional[list[str]] = None
) -> dict[str, Any]:
    """Retrieve the most recent sample for one or more tags."""
    request_id = set_request_id()
    tag_list_for_log = [tag_names] if isinstance(tag_names, str) else list(tag_names)
    log.info(
        "get_last_known_values_called",
        tag_names=tag_list_for_log,
        request_id=request_id,
        tool="get_last_known_values",
    )

    try:
        if isinstance(tag_names, str):
            tag_list = [tag_names]
        else:
            tag_list = list(tag_names)

        if not tag_list or all(not tag.strip() for tag in tag_list):
            return {
                "success": False,
                "error": "Tag names cannot be empty",
                "data": [],
                "count": 0,
                "tag_names": tag_list,
            }

        lookup_tags, resolved_map = await _resolve_tag_identifiers(tag_list, include_original=False)
        request_tags = lookup_tags or tag_list

        views_base_url = os.getenv("CANARY_VIEWS_BASE_URL", "")
        if not views_base_url:
            raise ValueError("CANARY_VIEWS_BASE_URL not configured")

        async with CanaryAuthClient() as client:
            api_token = await client.get_valid_token()

            data_url = f"{views_base_url}/api/v2/getTagData"

            async with httpx.AsyncClient(timeout=30.0) as http_client:
                lookback_hours = max(1, int(os.getenv("CANARY_LAST_VALUE_LOOKBACK_HOURS", "24")))
                page_size = max(1, int(os.getenv("CANARY_LAST_VALUE_PAGE_SIZE", "500")))
                now_utc = datetime.now(UTC)
                start_window = now_utc - timedelta(hours=lookback_hours)

                payload = {
                    "apiToken": api_token,
                    "tags": request_tags,
                    "startTime": _isoformat_utc(start_window),
                    "endTime": _isoformat_utc(now_utc),
                    "pageSize": page_size,
                }
                if views:
                    payload["views"] = views
                else:
                    default_view = os.getenv("CANARY_DEFAULT_VIEW")
                    if default_view:
                        payload["views"] = [default_view]

                response = await http_client.post(data_url, json=payload)
                response.raise_for_status()
                api_response = response.json()

        data_points, _ = _parse_canary_timeseries_payload(api_response)

        latest_by_tag: dict[str, dict[str, Any]] = {}
        for point in data_points:
            tag_name = point.get("tagName")
            ts = _parse_iso_timestamp(point.get("timestamp"))
            if not tag_name or ts is None:
                continue
            existing = latest_by_tag.get(tag_name)
            if not existing or ts > existing["_ts"]:
                cloned = dict(point)
                cloned["_ts"] = ts
                latest_by_tag[tag_name] = cloned

        if latest_by_tag:
            data_points = []
            for entry in latest_by_tag.values():
                entry.pop("_ts", None)
                data_points.append(entry)
            data_points.sort(
                key=lambda item: _parse_iso_timestamp(item.get("timestamp"))
                or datetime.min.replace(tzinfo=UTC),
                reverse=True,
            )

        if resolved_map:
            for point in data_points:
                tag_name = point.get("tagName")
                original = next((k for k, v in resolved_map.items() if v == tag_name), None)
                if original:
                    point["requestedTag"] = original

        if isinstance(api_response, dict) and "error" in api_response:
            error_msg = api_response.get("error", "Unknown error")
            return {
                "success": False,
                "error": error_msg,
                "data": [],
                "count": 0,
                "tag_names": tag_list,
            }

        log.info(
            "get_last_known_values_success",
            tag_names=tag_list,
            data_point_count=len(data_points),
            request_id=get_request_id(),
        )
        return {
            "success": True,
            "data": data_points,
            "count": len(data_points),
            "tag_names": tag_list,
            "resolved_tag_names": resolved_map,
        }

    except CanaryAuthError as e:
        error_msg = f"Authentication failed: {str(e)}"
        log.error(
            "get_last_known_values_auth_failed",
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
        error_msg = f"API request failed with status {e.response.status_code}: {e.response.text}"
        log.error(
            "get_last_known_values_api_error",
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
            "get_last_known_values_network_error",
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
        error_msg = f"Unexpected error retrieving last known values: {str(e)}"
        log.error(
            "get_last_known_values_unexpected_error",
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
async def read_timeseries(
    tag_names: str | list[str],
    start_time: str,
    end_time: str,
    views: Optional[list[str]] = None,
    page_size: int = 1000,
) -> dict[str, Any]:
    """
    Retrieve historical timeseries data for specific tags and time ranges.

    This tool retrieves historical process data from the Canary historian
    for analysis and troubleshooting.

    Args:
        tag_names: Single tag name or list of tag names to retrieve data for
        start_time: Start time (ISO timestamp or relative expression like "now-1d")
        end_time: End time (ISO timestamp or relative expression like "now")
        page_size: Number of samples per page (default 1000)

    Returns:
        dict[str, Any]: Dictionary containing timeseries data with keys:
            - data: List of data points with timestamp, value, quality
            - count: Total number of data points returned
            - success: Boolean indicating if operation succeeded
            - tag_names: The tag names that were queried
            - start_time: The start time used for the query
            - end_time: The end time used for the query

    Raises:
        Exception: If authentication fails or API request errors occur

    Note:
        When retrieving data for multiple tags, the MCP issues POST requests to the Canary
        historian. Avoid multi-tag GET queries to remain compatible with the API.
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

        # Get Canary Views base URL from environment
        views_base_url = os.getenv("CANARY_VIEWS_BASE_URL", "")
        if not views_base_url:
            raise ValueError("CANARY_VIEWS_BASE_URL not configured")

        # Authenticate and get API token
        lookup_tags, resolved_tag_map = await _resolve_tag_identifiers(
            tag_list, include_original=False
        )
        request_tags = lookup_tags or tag_list

        async with CanaryAuthClient() as client:
            api_token = await client.get_valid_token()

            # Query Canary API for timeseries data
            # Using getTagData endpoint to retrieve historical data
            data_url = f"{views_base_url}/api/v2/getTagData"

            async with httpx.AsyncClient(timeout=30.0) as http_client:
                payload = {
                    "apiToken": api_token,
                    "tags": request_tags,
                    "startTime": parsed_start_time,
                    "endTime": parsed_end_time,
                    "pageSize": page_size,
                }
                if views:
                    payload["views"] = views
                else:
                    default_view = os.getenv("CANARY_DEFAULT_VIEW")
                    if default_view:
                        payload["views"] = [default_view]

                response = await http_client.post(data_url, json=payload)

                response.raise_for_status()
                api_response = response.json()

        data_points, continuation = _parse_canary_timeseries_payload(api_response)

        if resolved_tag_map:
            for point in data_points:
                tag_name = point.get("tagName")
                if tag_name in resolved_tag_map.values():
                    continue
                original = next((k for k, v in resolved_tag_map.items() if v == tag_name), None)
                if original:
                    point["requestedTag"] = original

        if isinstance(api_response, dict) and "error" in api_response:
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

        if not data_points:
            last_values_result = await get_last_known_values.fn(tag_names=tag_list)
            if last_values_result.get("success") and last_values_result.get("data"):
                log.info(
                    "read_timeseries_fallback_last_known",
                    tag_names=tag_list,
                    request_id=get_request_id(),
                )
                return {
                    "success": True,
                    "data": last_values_result.get("data", []),
                    "count": last_values_result.get("count", 0),
                    "tag_names": tag_list,
                    "start_time": parsed_start_time,
                    "end_time": parsed_end_time,
                    "source": "last_known",
                    "resolved_tag_names": resolved_tag_map,
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
            "continuation": continuation,
            "resolved_tag_names": resolved_tag_map,
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
        error_msg = f"API request failed with status {e.response.status_code}: {e.response.text}"
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
                raw_timezones: list[str] = []
                if isinstance(timezones_data, dict):
                    raw_timezones = list(timezones_data.get("timeZones", []))
                elif isinstance(timezones_data, list):
                    raw_timezones = list(timezones_data)

                preferred_timezone = DEFAULT_TIMEZONE
                timezones: list[str] = []
                for tz in raw_timezones:
                    if isinstance(tz, str) and tz not in timezones:
                        timezones.append(tz)

                if preferred_timezone:
                    if preferred_timezone in timezones:
                        timezones.remove(preferred_timezone)
                    timezones.insert(0, preferred_timezone)

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
                        timezones[:10]
                        if len(timezones) > 10
                        else timezones
                    ),
                    "total_timezones": len(timezones),
                    "default_timezone": preferred_timezone,
                    "timezone_hint": (
                        f"Natural-language time ranges are interpreted in {preferred_timezone} "
                        "before converting to UTC."
                    ),
                    # Limit to 10 for readability
                    "supported_aggregates": (
                        aggregates[:10]
                        if isinstance(aggregates, list) and len(aggregates) > 10
                        else aggregates
                    ),
                    "total_aggregates": len(aggregates) if isinstance(aggregates, list) else 0,
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
        error_msg = f"API request failed with status {e.response.status_code}: {e.response.text}"
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
                "message": "Not initialized yet",
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
        "WARNING: Configuration validation disabled - server will start but API calls may fail",
        file=sys.stderr,
    )
    print(
        "         Please verify your CANARY_SAF_BASE_URL and CANARY_VIEWS_BASE_URL settings",
        file=sys.stderr,
    )

    transport = os.getenv("CANARY_MCP_TRANSPORT", "stdio").lower()
    if transport == "http":
        host = os.getenv("CANARY_MCP_HOST", "0.0.0.0")
        port = int(os.getenv("CANARY_MCP_PORT", "6000"))
        log.info("MCP server starting", transport=transport, host=host, port=port)
        mcp.run(transport="http", host=host, port=port)
    else:
        log.info("MCP server starting", transport="stdio")
        mcp.run()
    log.info("MCP server stopped")


if __name__ == "__main__":
    main()
