"""Local tag index built from Canary documentation artifacts.

This module provides a lightweight search index over the
``docs/aux_files/Canary_Path_description_maceira.json`` file so that the MCP
server can translate natural-language tag descriptions into concrete Canary
paths even when the live API search yields poor results.
"""

from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

import numpy as np

from canary_mcp.logging_setup import get_logger
from canary_mcp.vector_utils import hash_embedding

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
        default_path = (
            repo_root / "docs" / "aux_files" / "Canary_Path_description_maceira.json"
        )
        if dataset_path is not None:
            resolved_path = dataset_path
        else:
            resolved_path = default_path
            if not resolved_path.exists():
                # Preferred alternate path under Canary Resources
                resources_alt = (
                    repo_root
                    / "docs"
                    / "aux_files"
                    / "Canary Resources"
                    / "Canary_Path_description_maceira.json"
                )
                mcp_debug_alt = (
                    repo_root
                    / "docs"
                    / "aux_files"
                    / "mcp debug aux"
                    / "Canary_Path_description_maceira.json"
                )
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


class VectorTagRetriever:
    """Wrapper around the offline embeddings produced by scripts/build_vector_index.py."""

    def __init__(
        self,
        index_dir: Path,
        *,
        top_k: int = 10,
        dimension: Optional[int] = None,
        seed: int = 0,
    ) -> None:
        self.index_dir = index_dir
        self.top_k = top_k
        self.dimension_override = dimension
        self.seed = seed
        self._loaded = False
        self._available = False
        self._embeddings: Optional[np.ndarray] = None
        self._records: list[dict[str, Any]] = []
        self._dimension = dimension or int(os.getenv("CANARY_VECTOR_DIM", "512"))

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return

        embeddings_path = self.index_dir / "embeddings.npy"
        records_path = self.index_dir / "records.json"
        meta_path = self.index_dir / "meta.json"

        if not embeddings_path.exists() or not records_path.exists():
            log.warning(
                "vector_index_missing_files",
                embeddings=str(embeddings_path),
                records=str(records_path),
            )
            self._loaded = True
            return

        try:
            embeddings = np.load(embeddings_path)
            records = json.loads(records_path.read_text(encoding="utf-8"))
            meta = (
                json.loads(meta_path.read_text(encoding="utf-8"))
                if meta_path.exists()
                else {}
            )
            dimension = int(meta.get("dimension", embeddings.shape[1]))
            seed = int(meta.get("seed", self.seed))
        except Exception as exc:  # pragma: no cover - defensive logging
            log.error(
                "vector_index_load_failed",
                error=str(exc),
                index_dir=str(self.index_dir),
                exc_info=True,
            )
            self._loaded = True
            return

        self._embeddings = embeddings.astype(np.float32)
        self._records = records
        self._dimension = self.dimension_override or dimension
        self.seed = seed
        self._available = True
        self._loaded = True

        log.info(
            "vector_index_loaded",
            index_dir=str(self.index_dir),
            record_count=len(records),
            dimension=int(embeddings.shape[1]),
            seed=seed,
        )

    def search(self, text: str, *, limit: int = 10) -> List[Dict[str, Any]]:
        if not text:
            return []
        self._ensure_loaded()
        if not self._available or self._embeddings is None:
            return []

        query_vector = hash_embedding(
            text, dimension=self._dimension, seed=self.seed
        ).astype(np.float32)
        scores = self._embeddings @ query_vector
        top_k = min(limit or self.top_k, self.top_k)
        top_indices = np.argsort(scores)[::-1][:top_k]

        results: List[Dict[str, Any]] = []
        for idx in top_indices:
            record = self._records[int(idx)]
            results.append(
                {
                    **record,
                    "score": float(scores[idx]),
                    "source": "vector-index",
                }
            )
        return results


def _vector_search_enabled() -> bool:
    raw = os.getenv("CANARY_ENABLE_VECTOR_SEARCH", "false").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _vector_index_path() -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    default_path = repo_root / "data" / "vector-index"
    raw = os.getenv("CANARY_VECTOR_INDEX_PATH")
    return Path(raw) if raw else default_path


_VECTOR_RETRIEVER: Optional[VectorTagRetriever] = None


def _get_vector_retriever() -> Optional[VectorTagRetriever]:
    global _VECTOR_RETRIEVER
    if _VECTOR_RETRIEVER is not None:
        return _VECTOR_RETRIEVER
    if not _vector_search_enabled():
        return None
    index_dir = _vector_index_path()
    retriever = VectorTagRetriever(
        index_dir,
        top_k=int(os.getenv("CANARY_VECTOR_TOP_K", "10")),
        dimension=int(os.getenv("CANARY_VECTOR_DIM", "512")),
        seed=int(os.getenv("CANARY_VECTOR_HASH_SEED", "0")),
    )
    _VECTOR_RETRIEVER = retriever
    return retriever


def get_local_tag_candidates(
    keywords: Sequence[str],
    *,
    description: Optional[str] = None,
    limit: int = 25,
) -> List[Dict[str, Any]]:
    """Convenience wrapper used by the MCP server."""
    keyword_results = _LOCAL_TAG_INDEX.search(
        keywords, description=description, limit=limit
    )
    if not description or limit <= len(keyword_results):
        return keyword_results[:limit]

    retriever = _get_vector_retriever()
    if not retriever:
        return keyword_results[:limit]

    vector_limit = max(0, limit - len(keyword_results))
    vector_matches = retriever.search(description, limit=vector_limit * 2)

    if not vector_matches:
        return keyword_results[:limit]

    seen_paths = {item["path"] for item in keyword_results}
    for match in vector_matches:
        path = match.get("path")
        if not path or path in seen_paths:
            continue
        keyword_results.append(
            {
                "path": path,
                "name": path.split(".")[-1],
                "description": match.get("description", ""),
                "unit": match.get("unit", ""),
                "plant": match.get("plant", ""),
                "equipment": match.get("equipment", ""),
                "matched_tokens": [],
                "metadata": {
                    "path": path,
                    "description": match.get("description", ""),
                    "unit": match.get("unit", ""),
                    "plant": match.get("plant", ""),
                    "equipment": match.get("equipment", ""),
                    "source": "vector-index",
                    "score": match.get("score"),
                },
            }
        )
        seen_paths.add(path)
        if len(keyword_results) >= limit:
            break

    return keyword_results[:limit]
