#!/usr/bin/env python3
"""Generate JSONL + hash-based vector index from the Canary tag catalog (Story 4.10)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Iterable

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from canary_mcp.vector_utils import hash_embedding  # noqa: E402


def _iter_tags(payload: Any) -> Iterable[dict[str, Any]]:
    if isinstance(payload, list):
        for item in payload:
            yield from _iter_tags(item)
    elif isinstance(payload, dict):
        if "tags" in payload and isinstance(payload["tags"], list):
            for tag in payload["tags"]:
                if isinstance(tag, dict):
                    yield tag
        else:
            yield payload


def load_records(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    records: list[dict[str, Any]] = []
    for tag in _iter_tags(data):
        path_value = tag.get("path") or ""
        if not path_value:
            continue
        description = tag.get("description") or ""
        unit = tag.get("unit") or ""
        plant = tag.get("plant") or tag.get("site") or ""
        equipment = tag.get("equipment") or tag.get("area") or ""
        search_blob_parts = [
            path_value.replace(".", " "),
            description,
            unit,
            plant,
            equipment,
        ]
        doc_text = " ".join(part for part in search_blob_parts if part).strip()
        if not doc_text:
            doc_text = path_value
        records.append(
            {
                "path": path_value,
                "description": description,
                "unit": unit,
                "plant": plant,
                "equipment": equipment,
                "document_text": doc_text,
            }
        )
    return records


def write_jsonl(records: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def build_embeddings(
    records: list[dict[str, Any]],
    output_dir: Path,
    *,
    dimension: int = 512,
    seed: int = 0,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    embeddings = np.vstack(
        [
            hash_embedding(record["document_text"], dimension=dimension, seed=seed)
            for record in records
        ]
    )

    np.save(output_dir / "embeddings.npy", embeddings)
    distilled_records = [
        {k: v for k, v in record.items() if k != "document_text"} for record in records
    ]
    (output_dir / "records.json").write_text(
        json.dumps(distilled_records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    meta = {
        "record_count": len(records),
        "dimension": int(embeddings.shape[1]),
        "embedding_type": "hashed-sha256",
        "seed": seed,
    }
    (output_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build hash-based vector index from Canary catalog"
    )
    parser.add_argument(
        "--source",
        required=True,
        type=Path,
        help="Path to the Canary_Path_description_maceira.json file",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("data/vector-index"),
        help="Output directory for JSONL + embeddings",
    )
    parser.add_argument(
        "--dimension",
        type=int,
        default=int(os.getenv("CANARY_VECTOR_DIM", "512")),
        help="Embedding dimension (default 512)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=int(os.getenv("CANARY_VECTOR_HASH_SEED", "0")),
        help="Deterministic hash seed (default 0)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = load_records(args.source)
    if not records:
        raise SystemExit(f"No records found in {args.source}")

    jsonl_path = args.out / "catalog.jsonl"
    write_jsonl(records, jsonl_path)
    print(f"Wrote normalized JSONL to {jsonl_path}")

    build_embeddings(records, args.out, dimension=args.dimension, seed=args.seed)
    print(f"Vector index generated under {args.out}")


if __name__ == "__main__":
    main()
