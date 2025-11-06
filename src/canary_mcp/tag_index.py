"""Local tag index built from Canary documentation artifacts.

This module provides a lightweight search index over the
``docs/aux_files/Canary_Path_description_maceira.json`` file so that the MCP
server can translate natural-language tag descriptions into concrete Canary
paths even when the live API search yields poor results.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

from canary_mcp.logging_setup import get_logger

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+")

# Cap the number of postings kept per token to keep memory in check while still
# covering the majority of relevant candidates.
DEFAULT_MAX_POSTINGS_PER_TOKEN = 750

log = get_logger(__name__)


@dataclass(frozen=True)
class TagRecord:
    """Represents a single tag entry sourced from the Canary path export."""

    path: str
    name: str
    description: str
    unit: str
    plant: str
    equipment: str
    search_blob: str


class LocalTagIndex:
    """In-memory inverted index for quick keyword lookups."""

    def __init__(
        self,
        *,
        dataset_path: Optional[Path] = None,
        max_postings_per_token: int = DEFAULT_MAX_POSTINGS_PER_TOKEN,
    ) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        default_path = repo_root / "docs" / "aux_files" / "Canary_Path_description_maceira.json"
        if dataset_path is not None:
            resolved_path = dataset_path
        else:
            resolved_path = default_path
            if not resolved_path.exists():
                # Preferred alternate path under Canary Resources
                resources_alt = repo_root / "docs" / "aux_files" / "Canary Resources" / "Canary_Path_description_maceira.json"
                mcp_debug_alt = repo_root / "docs" / "aux_files" / "mcp debug aux" / "Canary_Path_description_maceira.json"
                for alt in (resources_alt, mcp_debug_alt):
                    if alt.exists():
                        log.info(
                            "local_tag_index_using_alternate_dataset",
                            dataset=str(alt),
                        )
                        resolved_path = alt
                        break
        self.dataset_path = resolved_path
        self.max_postings_per_token = max_postings_per_token
        self._loaded = False
        self._records: List[TagRecord] = []
        self._token_to_ids: Dict[str, List[int]] = defaultdict(list)

    def _tokenize(self, text: str) -> List[str]:
        return [match.group(0).lower() for match in TOKEN_PATTERN.finditer(text)]

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return

        if not self.dataset_path.exists():
            log.warning(
                "local_tag_index_dataset_missing",
                dataset=str(self.dataset_path),
            )
            self._loaded = True
            return

        try:
            with self.dataset_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except Exception as exc:  # pragma: no cover - defensive logging
            log.error(
                "local_tag_index_dataset_load_failed",
                dataset=str(self.dataset_path),
                error=str(exc),
                exc_info=True,
            )
            self._loaded = True
            return

        records: List[TagRecord] = []
        token_to_ids: Dict[str, List[int]] = defaultdict(list)

        def _iter_tags(raw: Any) -> Iterable[Dict[str, Any]]:
            if isinstance(raw, list):
                for element in raw:
                    yield from _iter_tags(element)
            elif isinstance(raw, dict):
                if "tags" in raw and isinstance(raw["tags"], list):
                    for tag in raw["tags"]:
                        if isinstance(tag, dict):
                            yield tag

        for tag in _iter_tags(payload):
            path = tag.get("path") or ""
            if not path:
                continue

            description = tag.get("description") or ""
            unit = tag.get("unit") or ""
            plant = tag.get("plant") or ""
            equipment = tag.get("equipment") or ""

            name = path.split(".")[-1]
            search_blob_parts = [
                path.replace(".", " "),
                description,
                unit,
                plant,
                equipment,
            ]
            search_blob = " ".join(part for part in search_blob_parts if part).lower()
            tokens = set(self._tokenize(search_blob))
            if not tokens:
                continue

            record_index = len(records)
            records.append(
                TagRecord(
                    path=path,
                    name=name,
                    description=description,
                    unit=unit,
                    plant=plant,
                    equipment=equipment,
                    search_blob=search_blob,
                )
            )

            for token in tokens:
                postings = token_to_ids[token]
                if len(postings) >= self.max_postings_per_token:
                    continue
                postings.append(record_index)

        self._records = records
        self._token_to_ids = token_to_ids
        self._loaded = True

        log.info(
            "local_tag_index_loaded",
            dataset=str(self.dataset_path),
            tag_count=len(self._records),
            token_count=len(self._token_to_ids),
        )

    def search(
        self,
        keywords: Sequence[str],
        *,
        description: Optional[str] = None,
        limit: int = 25,
    ) -> List[Dict[str, Any]]:
        """Return candidate tags ranked by keyword overlap."""
        if limit <= 0:
            limit = 5

        self._ensure_loaded()
        if not self._records or not keywords:
            return []

        keyword_set: List[str] = [kw.lower() for kw in keywords if kw]
        if not keyword_set:
            return []

        candidate_hits: Dict[int, Set[str]] = defaultdict(set)
        match_strength: Dict[int, float] = defaultdict(float)

        for keyword in keyword_set:
            for record_id in self._token_to_ids.get(keyword, []):
                candidate_hits[record_id].add(keyword)
                match_strength[record_id] += 1.0

        # Fallback: if no direct token matches were found, scan the blob text.
        if not candidate_hits and description:
            lowered_description = description.lower()
            for record_id, record in enumerate(self._records):
                hits = [kw for kw in keyword_set if kw in record.search_blob]
                if not hits:
                    continue
                candidate_hits[record_id].update(hits)
                match_strength[record_id] += 0.5 * len(hits)
                if len(candidate_hits) >= limit * 4:
                    break

        if not candidate_hits:
            return []

        ranked_records = sorted(
            candidate_hits.keys(),
            key=lambda rec_id: (-match_strength[rec_id], rec_id),
        )[: limit * 2]

        results: List[Dict[str, Any]] = []
        for record_id in ranked_records:
            record = self._records[record_id]
            metadata = {
                "path": record.path,
                "description": record.description,
                "unit": record.unit,
                "plant": record.plant,
                "equipment": record.equipment,
                "source": "local-index",
            }
            results.append(
                {
                    "path": record.path,
                    "name": record.name,
                    "description": record.description,
                    "unit": record.unit,
                    "plant": record.plant,
                    "equipment": record.equipment,
                    "matched_tokens": sorted(candidate_hits[record_id]),
                    "metadata": metadata,
                }
            )
            if len(results) >= limit:
                break

        return results


_LOCAL_TAG_INDEX = LocalTagIndex()


def get_local_tag_candidates(
    keywords: Sequence[str],
    *,
    description: Optional[str] = None,
    limit: int = 25,
) -> List[Dict[str, Any]]:
    """Convenience wrapper used by the MCP server."""
    return _LOCAL_TAG_INDEX.search(keywords, description=description, limit=limit)
