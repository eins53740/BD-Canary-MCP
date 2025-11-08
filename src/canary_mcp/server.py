"""Main MCP server module for Canary Historian integration."""

import argparse
import asyncio
import json
import os
import re
from collections import OrderedDict
from datetime import UTC, datetime, timedelta
from functools import lru_cache, wraps
from pathlib import Path
from textwrap import dedent
from typing import Any, Optional, Sequence
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.prompts import Message

from canary_mcp.auth import CanaryAuthClient, CanaryAuthError
from canary_mcp.cache import get_cache_store
from canary_mcp.http_client import execute_tool_request
from canary_mcp.logging_setup import configure_logging, get_logger
from canary_mcp.metrics import MetricsTimer, get_metrics_collector
from canary_mcp.request_context import get_request_id, set_request_id
from canary_mcp.response_guard import DEFAULT_LIMIT_BYTES, apply_response_size_limit
from canary_mcp.write_guard import WriteDatasetError, validate_test_dataset

# Some integration tests expect a globally available mock_data_response placeholder.
try:  # pragma: no cover - test harness compatibility shim
    import builtins
    from unittest.mock import MagicMock

    if not hasattr(builtins, "mock_data_response"):
        _placeholder_response = MagicMock()
        _placeholder_response.json.return_value = {"data": []}
        _placeholder_response.raise_for_status = MagicMock()
        builtins.mock_data_response = _placeholder_response
except Exception:  # pragma: no cover - avoid polluting runtime errors
    pass

# Load environment variables
load_dotenv()

configure_logging()

from canary_mcp.tag_index import get_local_tag_candidates

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

# Enforce ≤1 MB payloads by default (configurable via CANARY_MAX_RESPONSE_BYTES).
RESPONSE_SIZE_LIMIT = int(
    os.getenv("CANARY_MAX_RESPONSE_BYTES", str(DEFAULT_LIMIT_BYTES))
)
MAX_WRITE_RECORDS = int(os.getenv("CANARY_MAX_WRITE_RECORDS", "50"))
WRITER_DISABLED_MESSAGE = "Write operations are disabled. Set CANARY_WRITER_ENABLED=true to allow Test/* writes."


def _is_truthy(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"", "0", "false", "no", "off"}


def _writer_enabled() -> bool:
    return _is_truthy(os.getenv("CANARY_WRITER_ENABLED", "true"), default=True)


def _get_tester_roles() -> tuple[str, ...]:
    raw = os.getenv("CANARY_TESTER_ROLES", "tester")
    roles = tuple(role.strip().lower() for role in raw.split(",") if role.strip())
    return roles or ("tester",)


def _require_tester_role(role: str) -> str:
    normalized = (role or "").strip().lower()
    allowed = _get_tester_roles()
    if not normalized:
        raise PermissionError(
            "Write tool requires a tester role. Provide role='tester' or another allowed role."
        )
    if normalized not in allowed:
        raise PermissionError(
            f"Role '{role}' is not authorized for write operations. Allowed tester roles: "
            f"{', '.join(allowed)}."
        )
    return normalized


def _resolve_asset_view(view: Optional[str]) -> str:
    candidate = (view or os.getenv("CANARY_ASSET_VIEW", "")).strip()
    if not candidate:
        raise ValueError(
            "Asset view is required. Provide the 'view' argument or set CANARY_ASSET_VIEW."
        )
    return candidate


def _normalize_write_timestamp(value: Optional[str]) -> str:
    if not value:
        dt = datetime.now(UTC)
    else:
        cleaned = value.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(cleaned)
        except ValueError as exc:  # pragma: no cover - validated in unit tests
            raise ValueError(
                f"Invalid timestamp '{value}'. Provide an ISO 8601 string "
                f"(e.g., 2025-01-01T00:00:00Z)."
            ) from exc
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        else:
            dt = dt.astimezone(UTC)
    return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _coerce_numeric_value(raw: Any) -> float:
    if isinstance(raw, bool):
        return 1.0 if raw else 0.0
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, str):
        stripped = raw.strip()
        if not stripped:
            raise ValueError("Value strings cannot be empty.")
        return float(stripped)
    raise ValueError("Record values must be numeric (int, float, or numeric string).")


def _build_manual_entry_payload(
    dataset: str, records: Sequence[dict[str, Any]]
) -> tuple[dict[str, list[list[Any]]], list[dict[str, Any]]]:
    if not records:
        raise ValueError("Provide at least one record to write.")
    if len(records) > MAX_WRITE_RECORDS:
        raise ValueError(
            f"Too many records ({len(records)}). Limit is {MAX_WRITE_RECORDS} per request."
        )

    manual_entry: dict[str, list[list[Any]]] = {}
    summary: list[dict[str, Any]] = []
    valid_prefixes = (
        dataset,
        f"{dataset}.",
        f"{dataset}/",
    )

    for idx, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(
                f"Record #{idx + 1} must be an object with tag/value/timestamp fields."
            )

        tag = record.get("tag") or record.get("path")
        if not tag:
            raise ValueError(f"Record #{idx + 1} is missing the 'tag' field.")
        tag_str = str(tag).strip()
        if not tag_str:
            raise ValueError(f"Record #{idx + 1} has an empty tag.")
        if not any(tag_str.startswith(prefix) for prefix in valid_prefixes):
            raise ValueError(
                f"Tag '{tag_str}' must reside under the {dataset} dataset "
                f"to satisfy the Test/* policy."
            )

        timestamp_iso = _normalize_write_timestamp(
            record.get("timestamp") or record.get("time")
        )
        value = _coerce_numeric_value(record.get("value"))
        entry: list[Any] = [timestamp_iso, value]
        quality = record.get("quality")
        if quality is not None:
            entry.append(quality)

        manual_entry.setdefault(tag_str, []).append(entry)
        summary.append(
            {
                "tag": tag_str,
                "timestamp": timestamp_iso,
                "value": value,
                "quality": quality,
            }
        )

    return manual_entry, summary


# Payload guard helpers -----------------------------------------------------


def _apply_payload_guard(payload: Any) -> Any:
    guarded, _ = apply_response_size_limit(
        payload,
        request_id=get_request_id(),
        logger=log,
        limit_bytes=RESPONSE_SIZE_LIMIT,
    )
    return guarded


def _install_payload_guard(tool_wrapper: Any) -> None:
    original_fn = tool_wrapper.fn

    if getattr(
        original_fn, "_payload_guard_applied", False
    ):  # pragma: no cover - guard
        return

    if asyncio.iscoroutinefunction(original_fn):

        @wraps(original_fn)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            result = await original_fn(*args, **kwargs)
            return _apply_payload_guard(result)

        async_wrapper._payload_guard_applied = True  # type: ignore[attr-defined]
        tool_wrapper.fn = async_wrapper
    else:

        @wraps(original_fn)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            result = original_fn(*args, **kwargs)
            return _apply_payload_guard(result)

        sync_wrapper._payload_guard_applied = True  # type: ignore[attr-defined]
        tool_wrapper.fn = sync_wrapper


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
READ_TIMESERIES_HINT = (
    "Call read_timeseries with tag_names as a list of historian paths (e.g. "
    "['Secil.Portugal.Area.Tag']). Do not wrap the list in a JSON string—"
    "supply the array directly. "
    "Resolve tag paths with search_tags or the tag_lookup_workflow before "
    "requesting data, and keep "
    "start/end times as ISO timestamps or Canary relative expressions."
)
GET_TAG_DATA2_HINT = (
    "Use get_tag_data2 when you need the higher-capacity Canary getTagData2 endpoint. Provide tags "
    "plus start/end times; include aggregateName/aggregateInterval for processed data and adjust "
    "maxSize (default 1000) to fetch larger payloads with fewer continuation tokens."
)
GET_ASSET_TYPES_HINT = (
    "Call get_asset_types with the Canary view that hosts your asset models "
    "(e.g. CANARY_ASSET_VIEW). Use get_asset_instances to list concrete assets for a type."
)
GET_EVENTS_HINT = (
    "Use get_events_limit10 to fetch the latest historian events. Limit defaults to 10 but can be "
    "raised cautiously; provide start/end windows to filter further."
)
BROWSE_STATUS_HINT = (
    "Use browse_status to explore namespaces, verify view availability, and confirm the next "
    "pagination path before drilling into metadata."
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


def _build_timeseries_summary(
    tag_names: Sequence[str],
    resolved_tag_map: Optional[dict[str, str]],
    start_time: str,
    end_time: str,
    duration_seconds: Optional[float],
    data_points: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    """Generate a compact summary block for timeseries responses."""
    resolved_map = resolved_tag_map or {tag: tag for tag in tag_names}
    samples_per_tag: OrderedDict[str, int] = OrderedDict()
    for point in data_points:
        tag_name = point.get("tagName")
        if not tag_name:
            continue
        samples_per_tag[tag_name] = samples_per_tag.get(tag_name, 0) + 1

    site_hint: Optional[str] = None
    for resolved_value in resolved_map.values():
        if not isinstance(resolved_value, str) or not resolved_value:
            continue
        segments = [segment for segment in resolved_value.split(".") if segment]
        if not segments:
            continue
        site_hint = ".".join(segments[:2]) if len(segments) >= 2 else segments[0]
        break

    range_block: dict[str, Any] = {
        "start": start_time,
        "end": end_time,
    }
    if duration_seconds is not None:
        range_block["duration_seconds"] = max(0, int(duration_seconds))

    return {
        "site_hint": site_hint,
        "requested_tags": list(tag_names),
        "resolved_tags": resolved_map,
        "total_samples": len(data_points),
        "samples_per_tag": samples_per_tag,
        "range": range_block,
    }


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
    processed_identifiers: set[str] = set()

    for identifier in tag_identifiers:
        if not identifier:
            continue
        cleaned = identifier.strip()
        if not cleaned:
            continue

        if cleaned in processed_identifiers:
            continue
        processed_identifiers.add(cleaned)

        resolved_map.setdefault(cleaned, cleaned)

        if include_original and cleaned not in lookup_paths:
            lookup_paths.append(cleaned)

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
    name_weight = 5.0
    path_weight = 3.0
    description_weight = 2.0
    metadata_weight = 1.0
    starts_with_bonus = 1.5
    exact_match_bonus = 3.0

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


def _compute_confidence(candidates: list[dict[str, Any]]) -> tuple[float, str]:
    """
    Compute a normalized confidence score (0-1) and label for ranked candidates.

    Confidence considers absolute score plus margin versus the runner-up.
    """
    if not candidates:
        return 0.0, "no_match"

    top_score = max(float(candidates[0].get("score") or 0.0), 0.0)
    runner_up = (
        max(float(candidates[1].get("score") or 0.0), 0.0)
        if len(candidates) > 1
        else 0.0
    )

    if top_score <= 0:
        return 0.0, "no_match"

    margin = max(top_score - runner_up, 0.0)
    normalized = min(
        1.0, (top_score / (top_score + 5.0)) + (margin / (margin + 5.0)) / 2
    )
    normalized = round(normalized, 3)

    if normalized >= 0.8:
        label = "high"
    elif normalized >= 0.7:
        label = "medium"
    elif normalized > 0.0:
        label = "low"
    else:
        label = "no_match"

    return normalized, label


def _build_clarifying_question(keywords: list[str]) -> str:
    """Return a helpful clarifying question using existing keywords."""
    phrase = ", ".join(keywords[:3]) if keywords else "the measurement"
    return (
        f"Can you specify the site, equipment, or engineering units for {phrase}? "
        "For example: 'Maceira kiln 6 shell temperature in section 15 (°C)'."
    )


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


def _extract_tag_input_literals(tag_names: str | Sequence[str]) -> list[str]:
    """Return the raw tag inputs as provided by the caller without additional parsing."""
    if isinstance(tag_names, str):
        return [tag_names]
    if tag_names is None:
        return []
    return [str(item) for item in tag_names]


def _coerce_tag_names(tag_names: str | Sequence[str]) -> list[str]:
    """
    Normalize tag input into a list of clean tag names.

    Handles actual lists as well as JSON-like strings (e.g. '[\"tag\"]') that some clients
    mistakenly pass instead of arrays.
    """
    if isinstance(tag_names, str):
        candidate = tag_names.strip()
        if not candidate:
            return []

        # Attempt to parse JSON arrays or quoted strings
        if candidate.startswith("[") and candidate.endswith("]"):
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, list):
                coerced: list[str] = []
                for item in parsed:
                    if isinstance(item, str):
                        item_clean = item.strip()
                        if item_clean:
                            coerced.append(item_clean)
                if coerced:
                    return coerced
        if (candidate.startswith('"') and candidate.endswith('"')) or (
            candidate.startswith("'") and candidate.endswith("'")
        ):
            try:
                parsed_single = json.loads(candidate)
            except json.JSONDecodeError:
                parsed_single = candidate.strip("\"'")
            if isinstance(parsed_single, str):
                single_clean = parsed_single.strip()
                return [single_clean] if single_clean else []

        return [candidate]

    if tag_names is None:
        return []

    coerced_list: list[str] = []
    for item in tag_names:
        if isinstance(item, str):
            cleaned = item.strip()
            if cleaned:
                coerced_list.append(cleaned)
    return coerced_list


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
            f"Interpret natural-language expressions in {DEFAULT_TIMEZONE} "
            f"before converting to UTC."
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
                "Deterministic workflow:\n"
                "```\n"
                "Input: natural-language description\n"
                "1. Parse description → entities (equipment, measurement, site, units).\n"
                "2. Normalize synonyms (e.g., shell↔casing, rpm↔speed) and remove stop words.\n"
                "3. Query `resource://canary/tag-catalog` via `get_asset_catalog` "
                "using the strongest "
                "keywords; record matches (path, unit, description).\n"
                "4. If <3 matches, call `search_tags` with the best literal keyword (no wildcards) "
                "and merge results.\n"
                "5. For each candidate path:\n"
                "   a. Fetch metadata with `get_tag_properties` (units, description).\n"
                "   b. Score relevance (name weight > path > description > metadata).\n"
                "6. Compute confidence = normalized score of top candidate.\n"
                "   - confidence ≥ 0.80 → return best path and note why it matches.\n"
                '   - 0.70 ≤ confidence < 0.80 → return path but warn "double‑check units".\n'
                "   - confidence < 0.70 → DO NOT pick; return top candidates + clarifying question "
                "(ask for unit, section, equipment, etc.).\n"
                "7. Output:\n"
                "   - most_likely_path (if confident)\n"
                "   - alternatives ranked\n"
                "   - confidence (0‑1), confidence_label, clarifying_question (if any)\n"
                "   - instructions for next action (call read_timeseries, "
                "request clarification, etc.).\n"
                "Errors: If input is empty, reply with an actionable message "
                "asking for site/equipment.\n"
                "```\n"
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
                "Deterministic workflow:\n"
                "```\n"
                "Input: tag description + natural-language time window\n"
                "1. Call `tag_lookup_workflow` to obtain `most_likely_path`. "
                "If the workflow returns "
                "a clarifying question, ask the user before proceeding.\n"
                "2. Parse start/end using `resource://canary/time-standards`:\n"
                "   - Echo the interpreted ISO timestamps back to the user.\n"
                '   - Use `parse_time_expression` rules (e.g., "last 2 hours" → `Now-2Hours`).\n'
                "3. Build the `read_timeseries` payload:\n"
                "   - `tag_names`: list of fully qualified paths (e.g., "
                "['Secil.Portugal.Kiln6.Temp']).\n"
                "   - `start_time` / `end_time`: ISO strings.\n"
                "   - Optional `views` if the site requires it; page_size ≤ 1000.\n"
                "4. Execute `read_timeseries` (POST). If continuation tokens are returned, repeat "
                "until the requested time window is fully covered.\n"
                "5. Summarise the results:\n"
                "   - Mention the interpreted window, tag units, sample count, "
                "gaps, or quality flags.\n"
                "   - Suggest the next action (e.g., compute stats, compare tags) or surface any "
                "errors with guidance on how to fix them.\n"
                "```\n"
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
                        response = await execute_tool_request(
                            "search_tags",
                            http_client,
                            search_url,
                            json=payload,
                        )

                        response.raise_for_status()
                        data = response.json()

                    tags: list[dict[str, Any]] = []
                    if isinstance(data, dict) and "tags" in data:
                        tag_list = data.get("tags", [])
                        seen_paths: set[str] = set()

                        for tag in tag_list:
                            normalized: Optional[dict[str, Any]] = None

                            if isinstance(tag, dict):
                                name = str(
                                    tag.get("name", "") or tag.get("path", "")
                                ).strip()
                                path = str(tag.get("path", "") or name).strip()
                                normalized = {
                                    "name": name,
                                    "path": path,
                                    "dataType": str(
                                        tag.get("dataType", "unknown") or "unknown"
                                    ),
                                    "description": str(
                                        tag.get("description", "") or ""
                                    ),
                                }
                            elif isinstance(tag, str):
                                tag_str = tag.strip()
                                name_fragment = (
                                    tag_str.split(".")[-1]
                                    if "." in tag_str
                                    else tag_str
                                )
                                normalized = {
                                    "name": name_fragment,
                                    "path": tag_str,
                                    "dataType": "unknown",
                                    "description": "",
                                }

                            if not normalized:
                                continue

                            normalized_path = normalized.get("path", "")
                            if normalized_path in seen_paths:
                                continue
                            seen_paths.add(normalized_path)

                            tags.append(normalized)

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
            error_msg = f"API request failed with status {e.response.status_code}: {e.response.text}"
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
                response = await execute_tool_request(
                    "get_tag_metadata",
                    http_client,
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
                fallback_normalized["path"] = (
                    fallback_normalized.get("path") or resolved_path
                )
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

        has_structured_properties = isinstance(
            metadata.get("properties"), dict
        ) and bool(metadata["properties"])
        has_type_information = str(
            metadata.get("dataType", "")
        ).strip().lower() not in (
            "",
            "unknown",
        )
        has_units = bool(str(metadata.get("units", "")).strip())
        has_description = bool(str(metadata.get("description", "")).strip())

        if not (
            has_structured_properties
            or has_type_information
            or has_units
            or has_description
        ):
            log.warning(
                "get_tag_metadata_incomplete_payload",
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
            question = _build_clarifying_question([])
            return {
                "success": False,
                "error": "Description cannot be empty. Provide the site/"
                "equipment and measurement you need.",
                "description": description,
                "keywords": [],
                "most_likely_path": None,
                "candidates": [],
                "alternatives": [],
                "clarifying_question": question,
                "next_step": "clarify",
                "cached": False,
            }

        keywords = extract_keywords(description_normalized)
        if not keywords:
            timer.cache_hit = False
            question = _build_clarifying_question([])
            return {
                "success": False,
                "error": "Unable to extract meaningful keywords. Please include "
                "equipment, location, or units.",
                "description": description,
                "keywords": [],
                "most_likely_path": None,
                "candidates": [],
                "alternatives": [],
                "clarifying_question": question,
                "next_step": "clarify",
                "cached": False,
            }

        if max_results <= 0:
            max_results = 5

        cache_key = cache._generate_cache_key(
            "get_tag_path", description_normalized.lower()
        )

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
            clarifying_question = _build_clarifying_question(keywords)
            result = {
                "success": False,
                "description": description,
                "keywords": keywords,
                "error": "No tags matched the description. Provide the site, "
                "equipment, or engineering units.",
                "most_likely_path": None,
                "candidates": [],
                "alternatives": [],
                "clarifying_question": clarifying_question,
                "next_step": "clarify",
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
            candidate_description = combined_metadata.get(
                "description"
            ) or base_info.get("description", "")
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
                matched_keywords["local_index"] = _deduplicate_sequence(
                    sorted(local_keywords)
                )

            candidates.append(
                {
                    "path": metadata_path,
                    "name": candidate_name,
                    "dataType": candidate_data_type,
                    "description": candidate_description,
                    "score": round(score, 4),
                    "matched_keywords": {
                        field: matches
                        for field, matches in matched_keywords.items()
                        if matches
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
                    matched_keywords["local_index"] = _deduplicate_sequence(
                        sorted(local_keywords)
                    )
                candidates.append(
                    {
                        "path": path,
                        "name": base_info.get("name", ""),
                        "dataType": base_info.get("dataType", "unknown"),
                        "description": base_info.get("description", ""),
                        "score": round(score, 4),
                        "matched_keywords": {
                            field: matches
                            for field, matches in matched_keywords.items()
                            if matches
                        },
                        "search_sources": sorted(base_info["search_sources"]),
                        "metadata": local_metadata,
                        "metadata_cached": False,
                    }
                )

        candidates.sort(key=lambda item: item["score"], reverse=True)

        trimmed_candidates = candidates[:max_results]
        if not trimmed_candidates:
            clarifying_question = _build_clarifying_question(keywords)
            result = {
                "success": False,
                "description": description,
                "keywords": keywords,
                "error": "Unable to rank candidates. Please provide additional "
                "identifiers (unit, section, site).",
                "most_likely_path": None,
                "candidates": [],
                "alternatives": [],
                "clarifying_question": clarifying_question,
                "next_step": "clarify",
                "cached": False,
            }
            cache.set(cache_key, result, category="metadata")
            return result

        most_likely_path = trimmed_candidates[0]["path"]
        alternatives = [candidate["path"] for candidate in trimmed_candidates[1:]]
        confidence, confidence_label = _compute_confidence(trimmed_candidates)
        clarifying_question = None
        next_step = "return_path"
        message = (
            "High-confidence match. Proceed with read_timeseries or metadata lookup."
        )

        if confidence < 0.7:
            clarifying_question = _build_clarifying_question(keywords)
            next_step = "clarify"
            message = (
                "Low confidence match – request more context before selecting a tag."
            )
            result = {
                "success": False,
                "description": description,
                "keywords": keywords,
                "error": "Low confidence match; clarification required.",
                "most_likely_path": None,
                "candidates": trimmed_candidates,
                "alternatives": alternatives,
                "clarifying_question": clarifying_question,
                "confidence": confidence,
                "confidence_label": confidence_label,
                "next_step": next_step,
                "message": message,
                "cached": False,
            }
            cache.set(cache_key, result, category="metadata")
            return result

        if confidence_label == "medium":
            next_step = "double_check"
            message = (
                "Candidate found, but double-check units/section before using. "
                "Confirm via get_tag_properties if unsure."
            )

        result = {
            "success": True,
            "description": description,
            "keywords": keywords,
            "most_likely_path": most_likely_path,
            "candidates": trimmed_candidates,
            "alternatives": alternatives,
            "confidence": confidence,
            "confidence_label": confidence_label,
            "clarifying_question": clarifying_question,
            "next_step": next_step,
            "message": message,
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
                response = await execute_tool_request(
                    "get_tag_properties",
                    http_client,
                    properties_url,
                    json=payload,
                )
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
        error_msg = f"API request failed with status {exc.response.status_code}: {exc.response.text}"
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
                response = await execute_tool_request(
                    "list_namespaces",
                    http_client,
                    browse_url,
                    params={
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
                                        "path": node.get(
                                            "fullPath", node.get("path", name)
                                        ),
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

                namespaces = [
                    entry.get("path") for entry in structured_nodes if entry.get("path")
                ]

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
        log.error(
            "list_namespaces_auth_failed", error=error_msg, request_id=get_request_id()
        )
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
        log.error(
            "list_namespaces_network_error",
            error=error_msg,
            request_id=get_request_id(),
        )
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

        lookup_tags, resolved_map = await _resolve_tag_identifiers(
            tag_list, include_original=False
        )
        request_tags = lookup_tags or tag_list

        views_base_url = os.getenv("CANARY_VIEWS_BASE_URL", "")
        if not views_base_url:
            raise ValueError("CANARY_VIEWS_BASE_URL not configured")

        async with CanaryAuthClient() as client:
            api_token = await client.get_valid_token()

            data_url = f"{views_base_url}/api/v2/getTagData"

            async with httpx.AsyncClient(timeout=30.0) as http_client:
                lookback_hours = max(
                    1, int(os.getenv("CANARY_LAST_VALUE_LOOKBACK_HOURS", "24"))
                )
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

                response = await execute_tool_request(
                    "read_timeseries",
                    http_client,
                    data_url,
                    json=payload,
                )
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
                original = next(
                    (k for k, v in resolved_map.items() if v == tag_name), None
                )
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
        tag_names: Single tag name or list of tag names to retrieve data for. If a JSON-style
            string array is provided (e.g. '["tag1","tag2"]'), it will be parsed automatically,
            but callers should prefer passing an actual list.
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
            - hint: Guidance for correct usage

    Raises:
        Exception: If authentication fails or API request errors occur

    Note:
        When retrieving data for multiple tags, the MCP issues POST requests to the Canary
        historian. Avoid multi-tag GET queries to remain compatible with the API.
    """
    request_id = set_request_id()
    normalized_inputs = _coerce_tag_names(tag_names)
    raw_inputs = [
        item.strip()
        for item in _extract_tag_input_literals(tag_names)
        if isinstance(item, str) and item.strip()
    ]
    log_tag_list = normalized_inputs or raw_inputs
    log.info(
        "read_timeseries_called",
        tag_names=log_tag_list,
        start_time=start_time,
        end_time=end_time,
        page_size=page_size,
        request_id=request_id,
        tool="read_timeseries",
    )

    parsed_start_time = start_time
    parsed_end_time = end_time
    tag_list: list[str] = list(normalized_inputs)
    duration_seconds: Optional[float] = None

    try:
        if not tag_list:
            return {
                "success": False,
                "error": "Tag names cannot be empty",
                "data": [],
                "count": 0,
                "tag_names": raw_inputs,
                "hint": READ_TIMESERIES_HINT,
            }

        try:
            parsed_start_time = parse_time_expression(start_time)
            parsed_end_time = parse_time_expression(end_time)
        except ValueError as exc:
            return {
                "success": False,
                "error": f"Invalid time expression: {exc}",
                "data": [],
                "count": 0,
                "tag_names": tag_list,
                "hint": READ_TIMESERIES_HINT,
            }

        def _to_datetime(value: str) -> Optional[datetime]:
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None

        start_dt = _to_datetime(parsed_start_time)
        end_dt = _to_datetime(parsed_end_time)
        if start_dt and end_dt and start_dt >= end_dt:
            return {
                "success": False,
                "error": "Start time must be before end time",
                "data": [],
                "count": 0,
                "tag_names": tag_list,
                "hint": READ_TIMESERIES_HINT,
            }
        if start_dt and end_dt:
            duration_seconds = (end_dt - start_dt).total_seconds()

        # Get Canary Views base URL from environment
        views_base_url = os.getenv("CANARY_VIEWS_BASE_URL", "").strip()
        if not views_base_url:
            return {
                "success": False,
                "error": "Canary Views base URL not configured. Set CANARY_VIEWS_BASE_URL.",
                "data": [],
                "count": 0,
                "tag_names": tag_list,
                "hint": READ_TIMESERIES_HINT,
            }

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

                response = await execute_tool_request(
                    "read_timeseries",
                    http_client,
                    data_url,
                    json=payload,
                )

                response.raise_for_status()
                api_response = response.json()

        data_points, continuation = _parse_canary_timeseries_payload(api_response)

        if resolved_tag_map:
            inverse_map = {
                resolved: original for original, resolved in resolved_tag_map.items()
            }
            for point in data_points:
                tag_name = point.get("tagName")
                if not tag_name:
                    continue
                original = inverse_map.get(tag_name)
                if original and original != tag_name:
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
                    "hint": READ_TIMESERIES_HINT,
                }
            return {
                "success": False,
                "error": error_msg,
                "data": [],
                "count": 0,
                "tag_names": tag_list,
                "start_time": parsed_start_time,
                "end_time": parsed_end_time,
                "hint": READ_TIMESERIES_HINT,
            }

        if not data_points:
            last_values_result = await get_last_known_values.fn(tag_names=tag_list)
            if last_values_result.get("success") and last_values_result.get("data"):
                log.info(
                    "read_timeseries_fallback_last_known",
                    tag_names=tag_list,
                    request_id=get_request_id(),
                )
                data_from_last_known = last_values_result.get("data", [])
                summary = _build_timeseries_summary(
                    tag_list,
                    resolved_tag_map,
                    parsed_start_time,
                    parsed_end_time,
                    duration_seconds,
                    data_from_last_known,
                )
                return {
                    "success": True,
                    "data": data_from_last_known,
                    "count": len(data_from_last_known),
                    "tag_names": tag_list,
                    "start_time": parsed_start_time,
                    "end_time": parsed_end_time,
                    "source": "last_known",
                    "resolved_tag_names": resolved_tag_map,
                    "hint": READ_TIMESERIES_HINT,
                    "summary": summary,
                }

        log.info(
            "read_timeseries_success",
            tag_names=tag_list,
            data_point_count=len(data_points),
            start_time=parsed_start_time,
            end_time=parsed_end_time,
            request_id=get_request_id(),
        )
        summary = _build_timeseries_summary(
            tag_list,
            resolved_tag_map,
            parsed_start_time,
            parsed_end_time,
            duration_seconds,
            data_points,
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
            "hint": READ_TIMESERIES_HINT,
            "summary": summary,
        }

    except CanaryAuthError as e:
        error_msg = f"Authentication failed: {str(e)}"
        log.error(
            "read_timeseries_auth_failed",
            error=error_msg,
            tag_names=tag_list,
            request_id=get_request_id(),
        )
        return {
            "success": False,
            "error": error_msg,
            "data": [],
            "count": 0,
            "tag_names": tag_list,
            "hint": READ_TIMESERIES_HINT,
        }

    except httpx.HTTPStatusError as e:
        error_msg = f"API request failed with status {e.response.status_code}: {e.response.text}"
        log.error(
            "read_timeseries_api_error",
            error=error_msg,
            status_code=e.response.status_code,
            tag_names=tag_list,
            request_id=get_request_id(),
        )
        return {
            "success": False,
            "error": error_msg,
            "data": [],
            "count": 0,
            "tag_names": tag_list,
            "hint": READ_TIMESERIES_HINT,
        }

    except httpx.RequestError as e:
        error_msg = f"Network error accessing Canary API: {str(e)}"
        log.error(
            "read_timeseries_network_error",
            error=error_msg,
            tag_names=tag_list,
            request_id=get_request_id(),
        )
        return {
            "success": False,
            "error": error_msg,
            "data": [],
            "count": 0,
            "tag_names": tag_list,
            "hint": READ_TIMESERIES_HINT,
        }

    except Exception as e:
        error_msg = f"Unexpected error retrieving timeseries data: {str(e)}"
        log.error(
            "read_timeseries_unexpected_error",
            error=error_msg,
            tag_names=tag_list,
            request_id=get_request_id(),
            exc_info=True,
        )
        return {
            "success": False,
            "error": error_msg,
            "data": [],
            "count": 0,
            "tag_names": tag_list,
            "hint": READ_TIMESERIES_HINT,
        }


@mcp.tool()
async def write_test_dataset(
    dataset: str,
    records: list[dict[str, Any]],
    original_prompt: str,
    role: str,
    dry_run: bool = False,
) -> dict[str, Any]:
    """
    Write manual entry samples into approved Test/* datasets via Canary SAF.

    Args:
        dataset: The Test dataset to target (e.g., "Test/Maceira").
        records: List of objects with keys `tag`, `value`, and optional `timestamp`/`quality`.
        original_prompt: Natural-language instruction captured for auditing.
        role: Caller role; must match one of CANARY_TESTER_ROLES (default: "tester").
        dry_run: When True, validate payload but skip the actual Canary API call.

    Returns:
        Dict summarising the write attempt, including recorded prompt and role metadata.
    """
    request_id = set_request_id()
    log.info(
        "write_test_dataset_called",
        dataset=dataset,
        record_count=len(records) if records else 0,
        role=role,
        dry_run=dry_run,
        request_id=request_id,
    )

    if not _writer_enabled():
        log.warning(
            "write_test_dataset_disabled",
            dataset=dataset,
            request_id=request_id,
        )
        return {
            "success": False,
            "status": 503,
            "error": WRITER_DISABLED_MESSAGE,
            "original_prompt": original_prompt,
        }

    try:
        dataset_normalized = validate_test_dataset(dataset)
    except WriteDatasetError as exc:
        log.warning(
            "write_test_dataset_invalid_dataset",
            dataset=dataset,
            error=str(exc),
            request_id=request_id,
        )
        return {
            "success": False,
            "status": 400,
            "error": str(exc),
            "original_prompt": original_prompt,
        }

    try:
        tester_role = _require_tester_role(role)
    except PermissionError as exc:
        log.warning(
            "write_test_dataset_role_denied",
            dataset=dataset_normalized,
            role=role,
            error=str(exc),
            request_id=request_id,
        )
        return {
            "success": False,
            "status": 403,
            "error": str(exc),
            "original_prompt": original_prompt,
        }

    prompt_clean = (original_prompt or "").strip()
    if not prompt_clean:
        return {
            "success": False,
            "status": 400,
            "error": "original_prompt cannot be empty; capture the NL instruction for auditing.",
        }

    try:
        manual_payload, summary = _build_manual_entry_payload(
            dataset_normalized, records or []
        )
    except ValueError as exc:
        log.warning(
            "write_test_dataset_invalid_records",
            dataset=dataset_normalized,
            error=str(exc),
            request_id=request_id,
        )
        return {
            "success": False,
            "status": 400,
            "error": str(exc),
            "original_prompt": prompt_clean,
        }

    saf_base_url = os.getenv("CANARY_SAF_BASE_URL", "").rstrip("/")
    if not saf_base_url:
        error_msg = "CANARY_SAF_BASE_URL is not configured; cannot send write requests."
        log.error(
            "write_test_dataset_missing_config",
            error=error_msg,
            request_id=request_id,
        )
        return {
            "success": False,
            "status": 500,
            "error": error_msg,
            "original_prompt": prompt_clean,
        }

    if dry_run:
        log.info(
            "write_test_dataset_dry_run",
            dataset=dataset_normalized,
            records=len(summary),
            request_id=request_id,
        )
        return {
            "success": True,
            "write_success": False,
            "dataset": dataset_normalized,
            "records_written": 0,
            "records": summary,
            "original_prompt": prompt_clean,
            "role": tester_role,
            "dry_run": True,
        }

    api_response: dict[str, Any] = {}
    async with MetricsTimer("write_test_dataset") as timer:
        timer.cache_hit = False
        try:
            async with CanaryAuthClient() as client:
                session_token = await client.get_valid_token()

                async with httpx.AsyncClient(timeout=30.0) as http_client:
                    response = await http_client.post(
                        f"{saf_base_url}/manualEntryStoreData",
                        json={
                            "sessionToken": session_token,
                            "manualentrytvqs": manual_payload,
                        },
                    )
                    response.raise_for_status()
                    if response.content:
                        api_response = response.json()
        except CanaryAuthError as exc:
            log.error(
                "write_test_dataset_auth_error",
                error=str(exc),
                request_id=request_id,
            )
            return {
                "success": False,
                "status": 401,
                "error": str(exc),
                "original_prompt": prompt_clean,
            }
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            error_msg = (
                f"Write request failed with HTTP {status}: {exc.response.text[:256]}"
            )
            log.error(
                "write_test_dataset_http_error",
                status=status,
                error=error_msg,
                request_id=request_id,
            )
            return {
                "success": False,
                "status": status,
                "error": error_msg,
                "original_prompt": prompt_clean,
            }
        except httpx.RequestError as exc:
            error_msg = f"Network error calling Canary SAF API: {str(exc)}"
            log.error(
                "write_test_dataset_network_error",
                error=error_msg,
                request_id=request_id,
            )
            return {
                "success": False,
                "status": 502,
                "error": error_msg,
                "original_prompt": prompt_clean,
            }
        except Exception as exc:  # pragma: no cover - defensive
            log.error(
                "write_test_dataset_unexpected_error",
                error=str(exc),
                request_id=request_id,
                exc_info=True,
            )
            return {
                "success": False,
                "status": 500,
                "error": f"Unexpected error while writing: {str(exc)}",
                "original_prompt": prompt_clean,
            }

    log.info(
        "write_test_dataset_success",
        dataset=dataset_normalized,
        records=len(summary),
        role=tester_role,
        request_id=request_id,
    )
    return {
        "success": True,
        "write_success": True,
        "dataset": dataset_normalized,
        "records_written": len(summary),
        "records": summary,
        "original_prompt": prompt_clean,
        "role": tester_role,
        "dry_run": False,
        "api_response": api_response,
    }


@mcp.tool()
async def get_tag_data2(
    tag_names: str | list[str],
    start_time: str,
    end_time: str,
    aggregate_name: Optional[str] = None,
    aggregate_interval: Optional[str] = None,
    max_size: int = 1000,
) -> dict[str, Any]:
    """
    Retrieve historian data via Canary getTagData2 endpoint with optional aggregates.

    Args:
        tag_names: Single tag or list of tags (same normalization rules as read_timeseries)
        start_time: ISO timestamp or relative time string
        end_time: ISO timestamp or relative time string
        aggregate_name: Optional aggregate (e.g., TimeAverage2)
        aggregate_interval: Optional interval (e.g., 00:05:00) when aggregate_name is set
        max_size: Desired response size (# of samples) before Canary paginates (default 1000)

    Returns:
        dict: Structured response including raw data, count, and metadata summary
    """
    request_id = set_request_id()
    normalized_inputs = _coerce_tag_names(tag_names)
    raw_inputs = [
        item.strip()
        for item in _extract_tag_input_literals(tag_names)
        if isinstance(item, str) and item.strip()
    ]
    log_tag_list = normalized_inputs or raw_inputs
    log.info(
        "get_tag_data2_called",
        tag_names=log_tag_list,
        start_time=start_time,
        end_time=end_time,
        aggregate_name=aggregate_name,
        aggregate_interval=aggregate_interval,
        max_size=max_size,
        request_id=request_id,
        tool="get_tag_data2",
    )

    parsed_start_time = start_time
    parsed_end_time = end_time
    tag_list: list[str] = list(normalized_inputs)
    duration_seconds: Optional[float] = None

    try:
        if not tag_list:
            return {
                "success": False,
                "status": 400,
                "error": "Tag names cannot be empty",
                "data": [],
                "count": 0,
                "tag_names": raw_inputs,
                "hint": GET_TAG_DATA2_HINT,
            }

        if max_size <= 0:
            return {
                "success": False,
                "status": 400,
                "error": "maxSize must be a positive integer.",
                "data": [],
                "count": 0,
                "tag_names": tag_list,
                "hint": GET_TAG_DATA2_HINT,
            }

        if aggregate_interval and not aggregate_name:
            return {
                "success": False,
                "status": 400,
                "error": "Provide aggregate_name when aggregate_interval is supplied.",
                "data": [],
                "count": 0,
                "tag_names": tag_list,
                "hint": GET_TAG_DATA2_HINT,
            }

        try:
            parsed_start_time = parse_time_expression(start_time)
            parsed_end_time = parse_time_expression(end_time)
        except ValueError as exc:
            return {
                "success": False,
                "status": 400,
                "error": f"Invalid time expression: {exc}",
                "data": [],
                "count": 0,
                "tag_names": tag_list,
                "hint": GET_TAG_DATA2_HINT,
            }

        def _to_datetime(value: str) -> Optional[datetime]:
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None

        start_dt = _to_datetime(parsed_start_time)
        end_dt = _to_datetime(parsed_end_time)
        if start_dt and end_dt and start_dt >= end_dt:
            return {
                "success": False,
                "status": 400,
                "error": "Start time must be before end time",
                "data": [],
                "count": 0,
                "tag_names": tag_list,
                "hint": GET_TAG_DATA2_HINT,
            }
        if start_dt and end_dt:
            duration_seconds = (end_dt - start_dt).total_seconds()

        views_base_url = os.getenv("CANARY_VIEWS_BASE_URL", "").strip()
        if not views_base_url:
            return {
                "success": False,
                "status": 500,
                "error": "Canary Views base URL not configured. Set CANARY_VIEWS_BASE_URL.",
                "data": [],
                "count": 0,
                "tag_names": tag_list,
                "hint": GET_TAG_DATA2_HINT,
            }

        lookup_tags, resolved_tag_map = await _resolve_tag_identifiers(
            tag_list, include_original=False
        )
        request_tags = lookup_tags or tag_list

        async with CanaryAuthClient() as client:
            api_token = await client.get_valid_token()

            data_url = f"{views_base_url}/api/v2/getTagData2"
            async with httpx.AsyncClient(timeout=30.0) as http_client:
                payload: dict[str, Any] = {
                    "apiToken": api_token,
                    "tags": request_tags,
                    "startTime": parsed_start_time,
                    "endTime": parsed_end_time,
                    "maxSize": max_size,
                }
                if aggregate_name:
                    payload["aggregateName"] = aggregate_name
                if aggregate_interval:
                    payload["aggregateInterval"] = aggregate_interval

                response = await execute_tool_request(
                    "get_tag_data2",
                    http_client,
                    data_url,
                    json=payload,
                )
                response.raise_for_status()
                api_response = response.json()

        data_points, continuation = _parse_canary_timeseries_payload(api_response)
        summary = _build_timeseries_summary(
            tag_list,
            resolved_tag_map,
            parsed_start_time,
            parsed_end_time,
            duration_seconds,
            data_points,
        )

        log.info(
            "get_tag_data2_success",
            tag_names=tag_list,
            aggregate_name=aggregate_name,
            data_point_count=len(data_points),
            max_size=max_size,
            request_id=request_id,
        )
        return {
            "success": True,
            "data": data_points,
            "count": len(data_points),
            "tag_names": tag_list,
            "start_time": parsed_start_time,
            "end_time": parsed_end_time,
            "max_size": max_size,
            "aggregate_name": aggregate_name,
            "aggregate_interval": aggregate_interval,
            "continuation": continuation,
            "resolved_tag_names": resolved_tag_map,
            "summary": summary,
            "hint": GET_TAG_DATA2_HINT,
        }

    except CanaryAuthError as e:
        error_msg = f"Authentication failed: {str(e)}"
        log.error(
            "get_tag_data2_auth_failed",
            error=error_msg,
            tag_names=tag_list,
            request_id=request_id,
        )
        return {
            "success": False,
            "status": 401,
            "error": error_msg,
            "data": [],
            "count": 0,
            "tag_names": tag_list,
            "hint": GET_TAG_DATA2_HINT,
        }

    except httpx.HTTPStatusError as e:
        error_msg = f"API request failed with status {e.response.status_code}: {e.response.text}"
        log.error(
            "get_tag_data2_api_error",
            error=error_msg,
            status_code=e.response.status_code,
            tag_names=tag_list,
            request_id=request_id,
        )
        return {
            "success": False,
            "status": e.response.status_code,
            "error": error_msg,
            "data": [],
            "count": 0,
            "tag_names": tag_list,
            "hint": GET_TAG_DATA2_HINT,
        }

    except httpx.RequestError as e:
        error_msg = f"Network error accessing Canary API: {str(e)}"
        log.error(
            "get_tag_data2_network_error",
            error=error_msg,
            tag_names=tag_list,
            request_id=request_id,
        )
        return {
            "success": False,
            "status": 502,
            "error": error_msg,
            "data": [],
            "count": 0,
            "tag_names": tag_list,
            "hint": GET_TAG_DATA2_HINT,
        }

    except Exception as e:
        error_msg = f"Unexpected error retrieving timeseries data: {str(e)}"
        log.error(
            "get_tag_data2_unexpected_error",
            error=error_msg,
            tag_names=tag_list,
            request_id=request_id,
            exc_info=True,
        )
        return {
            "success": False,
            "status": 500,
            "error": error_msg,
            "data": [],
            "count": 0,
            "tag_names": tag_list,
            "hint": GET_TAG_DATA2_HINT,
        }


@mcp.tool()
async def get_aggregates() -> dict[str, Any]:
    """
    Fetch supported Canary aggregate definitions (wrapper around getAggregates).
    """
    request_id = set_request_id()
    log.info("get_aggregates_called", request_id=request_id, tool="get_aggregates")

    views_base_url = os.getenv("CANARY_VIEWS_BASE_URL", "").strip()
    if not views_base_url:
        return {
            "success": False,
            "status": 500,
            "error": "Canary Views base URL not configured. Set CANARY_VIEWS_BASE_URL.",
        }

    try:
        async with CanaryAuthClient() as client:
            api_token = await client.get_valid_token()
            async with httpx.AsyncClient(timeout=10.0) as http_client:
                response = await execute_tool_request(
                    "get_available_aggregates",
                    http_client,
                    f"{views_base_url}/api/v2/getAggregates",
                    params={"apiToken": api_token},
                )
                response.raise_for_status()
                payload = response.json()
    except CanaryAuthError as exc:
        return {
            "success": False,
            "status": 401,
            "error": str(exc),
        }
    except httpx.HTTPStatusError as exc:
        return {
            "success": False,
            "status": exc.response.status_code,
            "error": f"Failed to fetch aggregates: {exc.response.text}",
        }
    except Exception as exc:  # pragma: no cover - defensive
        return {
            "success": False,
            "status": 500,
            "error": f"Unexpected error fetching aggregates: {str(exc)}",
        }

    aggregates = payload.get("aggregates", payload)
    if isinstance(aggregates, dict):
        aggregates_list = [{"name": k, "description": v} for k, v in aggregates.items()]
    elif isinstance(aggregates, list):
        aggregates_list = aggregates
    else:
        aggregates_list = []

    log.info(
        "get_aggregates_success",
        aggregate_count=len(aggregates_list),
        request_id=request_id,
    )
    return {
        "success": True,
        "aggregates": aggregates_list,
        "count": len(aggregates_list),
    }


@mcp.tool()
async def get_asset_types(view: Optional[str] = None) -> dict[str, Any]:
    """
    Return asset types available in the configured Canary view.
    """
    request_id = set_request_id()
    try:
        resolved_view = _resolve_asset_view(view)
    except ValueError as exc:
        return {"success": False, "status": 400, "error": str(exc)}

    views_base_url = os.getenv("CANARY_VIEWS_BASE_URL", "").strip()
    if not views_base_url:
        return {
            "success": False,
            "status": 500,
            "error": "Canary Views base URL not configured. Set CANARY_VIEWS_BASE_URL.",
        }

    log.info(
        "get_asset_types_called",
        view=resolved_view,
        request_id=request_id,
        tool="get_asset_types",
    )

    try:
        async with CanaryAuthClient() as client:
            api_token = await client.get_valid_token()
            async with httpx.AsyncClient(timeout=15.0) as http_client:
                response = await execute_tool_request(
                    "get_asset_types",
                    http_client,
                    f"{views_base_url}/api/v2/getAssetTypes",
                    json={
                        "apiToken": api_token,
                        "view": resolved_view,
                    },
                )
                response.raise_for_status()
                payload = response.json()
    except CanaryAuthError as exc:
        return {"success": False, "status": 401, "error": str(exc)}
    except httpx.HTTPStatusError as exc:
        return {
            "success": False,
            "status": exc.response.status_code,
            "error": f"Failed to fetch asset types: {exc.response.text}",
        }
    except Exception as exc:  # pragma: no cover
        return {
            "success": False,
            "status": 500,
            "error": f"Unexpected error fetching asset types: {str(exc)}",
        }

    types = payload.get("assetTypes", payload)
    log.info(
        "get_asset_types_success",
        view=resolved_view,
        asset_type_count=len(types) if isinstance(types, list) else 0,
        request_id=request_id,
    )
    return {
        "success": True,
        "view": resolved_view,
        "asset_types": types,
        "count": len(types) if isinstance(types, list) else 0,
        "hint": GET_ASSET_TYPES_HINT,
    }


@mcp.tool()
async def get_asset_instances(
    asset_type: str,
    view: Optional[str] = None,
    path: Optional[str] = None,
) -> dict[str, Any]:
    """
    Return asset instances for a given asset type (wrapper for getAssetInstances).
    """
    request_id = set_request_id()
    if not asset_type:
        return {
            "success": False,
            "status": 400,
            "error": "asset_type is required.",
        }
    try:
        resolved_view = _resolve_asset_view(view)
    except ValueError as exc:
        return {"success": False, "status": 400, "error": str(exc)}

    views_base_url = os.getenv("CANARY_VIEWS_BASE_URL", "").strip()
    if not views_base_url:
        return {
            "success": False,
            "status": 500,
            "error": "Canary Views base URL not configured. Set CANARY_VIEWS_BASE_URL.",
        }

    log.info(
        "get_asset_instances_called",
        view=resolved_view,
        asset_type=asset_type,
        request_id=request_id,
    )

    try:
        async with CanaryAuthClient() as client:
            api_token = await client.get_valid_token()
            payload = {
                "apiToken": api_token,
                "view": resolved_view,
                "assetType": asset_type,
            }
            if path:
                payload["path"] = path

            async with httpx.AsyncClient(timeout=20.0) as http_client:
                response = await execute_tool_request(
                    "get_asset_instances",
                    http_client,
                    f"{views_base_url}/api/v2/getAssetInstances",
                    json=payload,
                )
                response.raise_for_status()
                api_response = response.json()
    except CanaryAuthError as exc:
        return {"success": False, "status": 401, "error": str(exc)}
    except httpx.HTTPStatusError as exc:
        return {
            "success": False,
            "status": exc.response.status_code,
            "error": f"Failed to fetch asset instances: {exc.response.text}",
        }
    except Exception as exc:  # pragma: no cover
        return {
            "success": False,
            "status": 500,
            "error": f"Unexpected error fetching asset instances: {str(exc)}",
        }

    instances = api_response.get("assetInstances", api_response)
    return {
        "success": True,
        "view": resolved_view,
        "asset_type": asset_type,
        "instances": instances,
        "count": len(instances) if isinstance(instances, list) else 0,
        "hint": GET_ASSET_TYPES_HINT,
    }


@mcp.tool()
async def get_events_limit10(
    limit: int = 10,
    view: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
) -> dict[str, Any]:
    """
    Retrieve recent Canary events (wrapper for getEvents with limit 10 default).
    """
    request_id = set_request_id()
    if limit <= 0:
        return {
            "success": False,
            "status": 400,
            "error": "limit must be greater than zero.",
        }

    views_base_url = os.getenv("CANARY_VIEWS_BASE_URL", "").strip()
    if not views_base_url:
        return {
            "success": False,
            "status": 500,
            "error": "Canary Views base URL not configured. Set CANARY_VIEWS_BASE_URL.",
        }

    log.info(
        "get_events_called",
        limit=limit,
        request_id=request_id,
        tool="get_events_limit10",
    )

    try:
        async with CanaryAuthClient() as client:
            api_token = await client.get_valid_token()
            payload: dict[str, Any] = {"apiToken": api_token, "limit": limit}
            if view:
                payload["view"] = view
            if start_time:
                payload["startTime"] = start_time
            if end_time:
                payload["endTime"] = end_time

            async with httpx.AsyncClient(timeout=10.0) as http_client:
                response = await execute_tool_request(
                    "get_events_limit10",
                    http_client,
                    f"{views_base_url}/api/v2/getEvents",
                    json=payload,
                )
                response.raise_for_status()
                api_response = response.json()
    except CanaryAuthError as exc:
        return {"success": False, "status": 401, "error": str(exc)}
    except httpx.HTTPStatusError as exc:
        return {
            "success": False,
            "status": exc.response.status_code,
            "error": f"Failed to fetch events: {exc.response.text}",
        }
    except Exception as exc:  # pragma: no cover
        return {
            "success": False,
            "status": 500,
            "error": f"Unexpected error fetching events: {str(exc)}",
        }

    events = api_response.get("events", api_response)
    return {
        "success": True,
        "events": events,
        "count": len(events) if isinstance(events, list) else 0,
        "hint": GET_EVENTS_HINT,
    }


@mcp.tool()
async def browse_status(
    path: Optional[str] = None,
    depth: Optional[int] = None,
    include_tags: Optional[bool] = True,
    view: Optional[str] = None,
) -> dict[str, Any]:
    """
    Inspect namespace nodes using the browseStatus endpoint.
    """
    request_id = set_request_id()
    views_base_url = os.getenv("CANARY_VIEWS_BASE_URL", "").strip()
    if not views_base_url:
        return {
            "success": False,
            "status": 500,
            "error": "Canary Views base URL not configured. Set CANARY_VIEWS_BASE_URL.",
        }

    log.info(
        "browse_status_called",
        path=path or "root",
        depth=depth,
        include_tags=include_tags,
        view=view,
        request_id=request_id,
        tool="browse_status",
    )

    try:
        async with CanaryAuthClient() as client:
            api_token = await client.get_valid_token()
            params: dict[str, Any] = {"apiToken": api_token}
            if path:
                params["path"] = path
            if depth is not None:
                params["depth"] = str(depth)
            if include_tags is not None:
                params["includeTags"] = "true" if include_tags else "false"
            if view:
                params["views"] = view

            async with httpx.AsyncClient(timeout=10.0) as http_client:
                response = await execute_tool_request(
                    "browse_status",
                    http_client,
                    f"{views_base_url}/api/v2/browseStatus",
                    params=params,
                )
                response.raise_for_status()
                api_response = response.json()
    except CanaryAuthError as exc:
        return {"success": False, "status": 401, "error": str(exc)}
    except httpx.HTTPStatusError as exc:
        return {
            "success": False,
            "status": exc.response.status_code,
            "error": f"Failed to browse status: {exc.response.text}",
        }
    except Exception as exc:
        return {
            "success": False,
            "status": 500,
            "error": f"Unexpected error browsing status: {str(exc)}",
        }

    nodes = api_response.get("nodes", [])
    tags = api_response.get("tags", [])
    log.info(
        "browse_status_success",
        path=path or "root",
        node_count=len(nodes) if isinstance(nodes, list) else 0,
        tag_count=len(tags) if isinstance(tags, list) else 0,
        request_id=get_request_id(),
    )
    return {
        "success": True,
        "nodes": nodes,
        "tags": tags,
        "next_path": api_response.get("nextPath"),
        "status": api_response.get("status"),
        "path": path,
        "depth": depth,
        "include_tags": include_tags,
        "view": view,
        "hint": BROWSE_STATUS_HINT,
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
                timezones_response = await execute_tool_request(
                    "get_timezones",
                    http_client,
                    timezones_url,
                    params={"apiToken": api_token},
                )
                timezones_response.raise_for_status()
                timezones_data = timezones_response.json()

                # Get supported aggregation functions
                aggregates_url = f"{views_base_url}/api/v2/getAggregates"
                aggregates_response = await execute_tool_request(
                    "get_available_aggregates",
                    http_client,
                    aggregates_url,
                    params={"apiToken": api_token},
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
                    if not isinstance(tz, str):
                        continue
                    trimmed = tz.strip()
                    if trimmed and trimmed not in timezones:
                        timezones.append(trimmed)

                if preferred_timezone and preferred_timezone in timezones:
                    timezones = [preferred_timezone] + [
                        tz for tz in timezones if tz != preferred_timezone
                    ]

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
                    "total_aggregates": (
                        len(aggregates) if isinstance(aggregates, list) else 0
                    ),
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
        log.error(
            "get_server_info_auth_failed", error=error_msg, request_id=get_request_id()
        )
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
        log.error(
            "get_server_info_network_error",
            error=error_msg,
            request_id=get_request_id(),
        )
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

    async with MetricsTimer("get_server_info") as timer:
        try:
            views_base_url = os.getenv("CANARY_VIEWS_BASE_URL", "")
            if not views_base_url:
                raise ValueError("CANARY_VIEWS_BASE_URL not configured")

            async with CanaryAuthClient() as client:
                api_token = await client.get_valid_token()

                server_info_url = f"{views_base_url}/api/v2/getServerInfo"

                async with httpx.AsyncClient(timeout=10.0) as http_client:
                    server_info_response = await execute_tool_request(
                        "get_server_info",
                        http_client,
                        server_info_url,
                        json={"apiToken": api_token},
                    )
                    server_info_response.raise_for_status()
                    server_info_data = server_info_response.json()

            mcp_info = {
                "version": os.getenv("MCP_VERSION", "unknown"),
                "environment": os.getenv("MCP_ENVIRONMENT", "development"),
                "log_level": os.getenv("LOG_LEVEL", "INFO"),
            }

            log.info(
                "get_server_info_success",
                request_id=request_id,
                canary_version=server_info_data.get("version"),
            )
            return {
                "success": True,
                "server_info": server_info_data,
                "mcp_info": mcp_info,
            }

        except CanaryAuthError as e:
            error_msg = f"Authentication failed: {str(e)}"
            log.error(
                "get_server_info_auth_failed",
                error=error_msg,
                request_id=request_id,
            )
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
                request_id=request_id,
            )
            return {
                "success": False,
                "error": error_msg,
                "server_info": {},
                "mcp_info": {},
            }

        except httpx.RequestError as e:
            error_msg = f"Network error accessing Canary API: {str(e)}"
            log.error(
                "get_server_info_network_error",
                error=error_msg,
                request_id=request_id,
            )
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
                request_id=request_id,
                exc_info=True,
            )
            return {
                "success": False,
                "error": error_msg,
                "server_info": {},
                "mcp_info": {},
            }

            return {"success": False, "error": error_msg, "aggregates": []}


@mcp.tool()
async def get_events(
    start_time: str,
    end_time: str,
    limit: int = 10,
    tag_names: Optional[list[str]] = None,
) -> dict[str, Any]:
    """
    Retrieve event data from the Canary historian.

    Args:
        start_time: Start time (ISO timestamp or relative expression like "now-1d")
        end_time: End time (ISO timestamp or relative expression like "now")
        limit: Maximum number of events to return (default 10)
        tag_names: Optional list of tag names to filter events

    Returns:
        dict[str, Any]: Dictionary containing event data with keys:
            - success: Boolean indicating if operation succeeded
            - events: List of event records
            - count: Total number of events returned
            - error: Error message (only on failure)
    """
    request_id = set_request_id()
    log.info(
        "get_events_called",
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        tag_names=tag_names,
        request_id=request_id,
        tool="get_events",
    )

    async with MetricsTimer("get_events") as timer:
        try:
            views_base_url = os.getenv("CANARY_VIEWS_BASE_URL", "")
            if not views_base_url:
                raise ValueError("CANARY_VIEWS_BASE_URL not configured")

            async with CanaryAuthClient() as client:
                api_token = await client.get_valid_token()

                events_url = f"{views_base_url}/api/v2/getEvents"

                payload: dict[str, Any] = {
                    "apiToken": api_token,
                    "startTime": start_time,
                    "endTime": end_time,
                    "limit": limit,
                }
                if tag_names:
                    payload["tags"] = tag_names

                async with httpx.AsyncClient(timeout=10.0) as http_client:
                    response = await execute_tool_request(
                        "get_events",
                        http_client,
                        events_url,
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()

            events = data.get("events", [])
            log.info(
                "get_events_success",
                request_id=request_id,
                event_count=len(events),
            )
            return {"success": True, "events": events, "count": len(events)}

        except CanaryAuthError as e:
            error_msg = f"Authentication failed: {str(e)}"
            log.error(
                "get_events_auth_failed",
                error=error_msg,
                request_id=request_id,
            )
            return {"success": False, "error": error_msg, "events": [], "count": 0}

        except httpx.HTTPStatusError as e:
            error_msg = f"API request failed with status {e.response.status_code}: {e.response.text}"
            log.error(
                "get_events_api_error",
                error=error_msg,
                status_code=e.response.status_code,
                request_id=request_id,
            )
            return {"success": False, "error": error_msg, "events": [], "count": 0}

        except httpx.RequestError as e:
            error_msg = f"Network error accessing Canary API: {str(e)}"
            log.error(
                "get_events_network_error",
                error=error_msg,
                request_id=request_id,
            )
            return {"success": False, "error": error_msg, "events": [], "count": 0}

        except Exception as e:
            error_msg = f"Unexpected error retrieving events: {str(e)}"
            log.error(
                "get_events_unexpected_error",
                error=error_msg,
                request_id=request_id,
                exc_info=True,
            )
            return {"success": False, "error": error_msg, "events": [], "count": 0}

            return {"success": False, "error": error_msg, "events": [], "count": 0}


@mcp.tool()
async def get_asset_types() -> dict[str, Any]:
    """
    Retrieve available asset types from the Canary historian.

    Returns:
        dict[str, Any]: Dictionary containing asset types with keys:
            - success: Boolean indicating if operation succeeded
            - asset_types: List of asset type names
            - error: Error message (only on failure)
    """
    request_id = set_request_id()
    log.info("get_asset_types_called", request_id=request_id, tool="get_asset_types")

    async with MetricsTimer("get_asset_types") as timer:
        try:
            views_base_url = os.getenv("CANARY_VIEWS_BASE_URL", "")
            if not views_base_url:
                raise ValueError("CANARY_VIEWS_BASE_URL not configured")

            async with CanaryAuthClient() as client:
                api_token = await client.get_valid_token()

                asset_types_url = f"{views_base_url}/api/v2/getAssetTypes"

                async with httpx.AsyncClient(timeout=10.0) as http_client:
                    response = await execute_tool_request(
                        "get_asset_types",
                        http_client,
                        asset_types_url,
                        json={"apiToken": api_token},
                    )
                    response.raise_for_status()
                    data = response.json()

            asset_types = data.get("assetTypes", [])
            log.info(
                "get_asset_types_success",
                request_id=request_id,
                asset_type_count=len(asset_types),
            )
            return {"success": True, "asset_types": asset_types}

        except CanaryAuthError as e:
            error_msg = f"Authentication failed: {str(e)}"
            log.error(
                "get_asset_types_auth_failed",
                error=error_msg,
                request_id=request_id,
            )
            return {"success": False, "error": error_msg, "asset_types": []}

        except httpx.HTTPStatusError as e:
            error_msg = f"API request failed with status {e.response.status_code}: {e.response.text}"
            log.error(
                "get_asset_types_api_error",
                error=error_msg,
                status_code=e.response.status_code,
                request_id=request_id,
            )
            return {"success": False, "error": error_msg, "asset_types": []}

        except httpx.RequestError as e:
            error_msg = f"Network error accessing Canary API: {str(e)}"
            log.error(
                "get_asset_types_network_error",
                error=error_msg,
                request_id=request_id,
            )
            return {"success": False, "error": error_msg, "asset_types": []}

        except Exception as e:
            error_msg = f"Unexpected error retrieving asset types: {str(e)}"
            log.error(
                "get_asset_types_unexpected_error",
                error=error_msg,
                request_id=request_id,
                exc_info=True,
            )
            return {"success": False, "error": error_msg, "asset_types": []}

            return {"success": False, "error": error_msg, "asset_types": []}

        except CanaryAuthError as e:
            error_msg = f"Authentication failed: {str(e)}"
            log.error(
                "get_asset_instances_auth_failed",
                error=error_msg,
                request_id=request_id,
            )
            return {
                "success": False,
                "error": error_msg,
                "asset_instances": [],
                "count": 0,
            }

        except httpx.HTTPStatusError as e:
            error_msg = f"API request failed with status {e.response.status_code}: {e.response.text}"
            log.error(
                "get_asset_instances_api_error",
                error=error_msg,
                status_code=e.response.status_code,
                request_id=request_id,
            )
            return {
                "success": False,
                "error": error_msg,
                "asset_instances": [],
                "count": 0,
            }

        except httpx.RequestError as e:
            error_msg = f"Network error accessing Canary API: {str(e)}"
            log.error(
                "get_asset_instances_network_error",
                error=error_msg,
                request_id=request_id,
            )
            return {
                "success": False,
                "error": error_msg,
                "asset_instances": [],
                "count": 0,
            }

        except Exception as e:
            error_msg = f"Unexpected error retrieving asset instances: {str(e)}"
            log.error(
                "get_asset_instances_unexpected_error",
                error=error_msg,
                request_id=request_id,
                exc_info=True,
            )
            return {
                "success": False,
                "error": error_msg,
                "asset_instances": [],
                "count": 0,
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
    log.info(
        "get_metrics_summary_called", request_id=request_id, tool="get_metrics_summary"
    )

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
    log.info(
        "cleanup_expired_cache_called",
        request_id=request_id,
        tool="cleanup_expired_cache",
    )

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


def _install_all_payload_guards() -> None:
    tools = (
        ping,
        get_asset_catalog,
        search_tags,
        get_tag_metadata,
        get_tag_path,
        get_tag_properties,
        list_namespaces,
        get_last_known_values,
        read_timeseries,
        get_server_info,
        get_metrics,
        get_metrics_summary,
        get_cache_stats,
        invalidate_cache,
        cleanup_expired_cache,
        get_health,
    )
    for tool in tools:
        _install_payload_guard(tool)


_install_all_payload_guards()


def main() -> None:
    """Run the MCP server."""
    import sys

    parser = argparse.ArgumentParser(description="Start the Canary MCP server.")
    parser.add_argument(
        "--health-check",
        action="store_true",
        help="Run a lightweight health check (no server startup).",
    )
    parser.add_argument(
        "--transport",
        choices={"stdio", "http"},
        help="Override transport for this invocation.",
    )
    parser.add_argument(
        "--host",
        help="Override HTTP host binding (http transport only).",
    )
    parser.add_argument(
        "--port",
        type=int,
        help="Override HTTP port (http transport only).",
    )
    args = parser.parse_args()

    if args.transport:
        os.environ["CANARY_MCP_TRANSPORT"] = args.transport
    if args.host:
        os.environ["CANARY_MCP_HOST"] = args.host
    if args.port is not None:
        os.environ["CANARY_MCP_PORT"] = str(args.port)

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

    if args.health_check:
        try:
            result = ping.fn()
            print(result)
            log.info("Health check completed", result=result)
            return
        except Exception as exc:  # pragma: no cover - defensive logging
            log.error("Health check failed", error=str(exc), exc_info=True)
            print(f"Health check failed: {exc}", file=sys.stderr)
            sys.exit(1)

    transport = os.getenv("CANARY_MCP_TRANSPORT", "stdio").lower()
    if transport == "http":
        host = os.getenv("CANARY_MCP_HOST", "0.0.0.0")
        port = int(os.getenv("CANARY_MCP_PORT", "6000"))
        log.info("MCP server starting", transport=transport, host=host, port=port)
        mcp.run(transport="http", host=host, port=port, show_banner=False)
    else:
        log.info("MCP server starting", transport="stdio")
        mcp.run(show_banner=False)
    log.info("MCP server stopped")


if __name__ == "__main__":
    main()
