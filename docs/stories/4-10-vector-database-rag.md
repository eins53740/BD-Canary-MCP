[x] # Story 4.10 — Vector Database RAG Foundation

Context & Constraints:
- Build on top of the existing flat Canary documentation (JSON/CSV under `docs/aux_files`).
- Keep everything local-first; the vector store can start embedded (FAISS/Chroma) but must expose a clean abstraction so it can migrate to a managed service later.
- Respect the current ≤1 MB response contract when returning RAG snippets to MCP clients.
- No production Canary calls during ingestion—use the on-disk resources only.

Acceptance Criteria (Checklist):
1. Conversion pipeline turns the current resources into normalized JSONL records (`path`, `description`, `units`, `site`, `document_text`, etc.).
2. Embedding + vector index creation script (`scripts/build_vector_index.py`) that ingests the JSONL file and produces a searchable index (local FAISS/Chroma folder).
3. Lightweight retrieval helper inside `canary_mcp.tag_index` (or new module) that, when enabled, can fetch top‑k semantic matches and merge them with the existing keyword index.
4. Configuration toggle (env var) to opt into vector retrieval without breaking the default inverted-index behaviour.
5. Documentation describing the ingestion pipeline, index format, and how to retrain/rebuild when new docs arrive (link from README + `docs/resources/resource-index.md`).

Validation:
- Run: `python scripts/build_vector_index.py --source docs/aux_files/Canary\ Resources/Canary_Path_description_maceira.json --out data/vector-index`.
- Run: `python -m pytest tests/unit/test_local_tag_index.py -k vector -q` (new tests covering the semantic helper).
- Manual smoke: call the helper with a free-form query (“section 15 kiln vibration”) and verify the semantic results line up with the legacy keyword lookup.

Deliverables:
- JSONL conversion artifact (ignored by git if large) + ingestion script.
- Local vector index scaffold and integration hook in the MCP server.
- Updated docs (README + resource index) outlining how to rebuild/extend the RAG database.

---

## Implementation Snapshot (2025-11-08)

- `scripts/build_vector_index.py` flattens the canonical catalog into JSONL and generates hash-based embeddings (`embeddings.npy`, `records.json`, `meta.json`) under `data/vector-index/`. The hash embedding keeps everything deterministic and lightweight (no GPU/torch dependency).
- `src/canary_mcp/tag_index.py` now includes `VectorTagRetriever`, guarded by `CANARY_ENABLE_VECTOR_SEARCH`. When enabled, `get_local_tag_candidates` appends semantic hits (flagged with `source="vector-index"`) to the existing keyword results while keeping the overall limit intact.
- New config knobs in `.env.example`: `CANARY_ENABLE_VECTOR_SEARCH`, `CANARY_VECTOR_INDEX_PATH`, `CANARY_VECTOR_TOP_K`, `CANARY_VECTOR_DIM`, and `CANARY_VECTOR_HASH_SEED`.
- Documentation: README explains how to build/rebuild the index and wire it into the MCP server; `docs/resources/resource-index.md` lists the new artifact in the resource inventory.
- Tests: `tests/unit/test_local_tag_index.py::test_get_local_tag_candidates_merges_vector_results` ensures semantic results are merged when the inverted index returns nothing.
- Validation commands from the story are now runnable:
  `python scripts/build_vector_index.py --source "docs/aux_files/Canary Resources/Canary_Path_description_maceira.json" --out data/vector-index`
  `python -m pytest tests/unit/test_local_tag_index.py -k vector -q -s`
