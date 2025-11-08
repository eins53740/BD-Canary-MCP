# Resource Index & RAG Notes

This repository ships all reference material locally so MCP clients can perform metadata lookups even when the Canary APIs are unavailable. The table below lists each resource, where it lives, and how the server uses it.

## 1. Canonical Tag Catalog (`Canary_Path_description_maceira.json`)
- **Location:** `docs/aux_files/Canary Resources/Canary_Path_description_maceira.json` (fallbacks: `docs/aux_files/Canary_Path_description_maceira.json`, `docs/aux_files/mcp debug aux/Canary_Path_description_maceira.json`)
- **Schema:** Array of objects with `path`, `description`, `unit`, `plant`, `equipment`, plus nested `tags` blocks.
- **Loader:** `LocalTagIndex` (`src/canary_mcp/tag_index.py`) builds an inverted index; `get_asset_catalog` exposes the same data through the MCP resource `resource://canary/tag-catalog`.
- **Usage:** feeds `get_tag_path`, `tag_lookup_workflow`, and any metadata-only search. The index enforces the global ≤1 MB response cap (`CANARY_MAX_RESPONSE_BYTES`) before returning samples.

## 2. Prompt/Workflow Resources
- **`docs/workflows/prompt-workflows.md`** – canonical instructions for `tag_lookup_workflow` and `timeseries_query_workflow`. Linked from README and prompts so LLMs follow deterministic steps.
- **`docs/resources/resource-index.md` (this file)** – reference for operators; mention it when documenting new tooling so everyone knows where data comes from.

## 3. Time Standards Resource
- **Location:** generated on-the-fly from `src/canary_mcp/server.py` but derived from the Canary docs (`docs/aux_files/maceira_postman_exampes.txt` and API references).
- **Schema:** `{ "default_timezone": "Europe/Lisbon", "relative_time_reference": "...", "examples": [...] }`
- **Usage:** `timeseries_query_workflow` and `read_timeseries` rely on it to interpret expressions; responses reiterate these examples to keep LLMs within spec.

## 4. Postman / API Fixture Files
- `docs/aux_files/maceira_postman_exampes.txt`, zipped Postman collections, and HTML exports under `docs/aux_files/Canary Resources/`.
- Used as human-readable references (not loaded at runtime) but can be converted to JSONL if we need additional metadata fields later.

## Metadata-Only Discovery (No Live API)
1. Call `get_asset_catalog` or read `resource://canary/tag-catalog` to pull candidate paths, units, and descriptions.
2. Use `get_local_tag_candidates(keywords, description, limit)` from `tag_index.py` to score matches purely from the catalog.
3. Combine the results with the new `confidence` field exposed by `get_tag_path`. Even without Canary online you can still propose the most likely historian path, then confirm once connectivity returns.
4. If the JSON resource grows beyond 1 MB for a single response, the payload guard (`CANARY_MAX_RESPONSE_BYTES`, default 1 000 000) automatically truncates and includes a preview plus guidance to narrow the query.

## 5. Vector Index (Semantic RAG)
- **Conversion:** `scripts/build_vector_index.py` flattens the canonical catalog into `data/vector-index/catalog.jsonl` and generates `embeddings.npy` + `records.json` using SentenceTransformers (default `all-MiniLM-L6-v2`).
- **Integration:** `src/canary_mcp/tag_index.py` loads the index when `CANARY_ENABLE_VECTOR_SEARCH=true` and merges top‑k semantic matches with the legacy inverted index.
- **Config knobs:**
  - `CANARY_ENABLE_VECTOR_SEARCH` – opt-in switch (default false).
  - `CANARY_VECTOR_INDEX_PATH` – location of the generated index folder (default `data/vector-index`).
  - `CANARY_VECTOR_TOP_K`, `CANARY_VECTOR_DIM`, `CANARY_VECTOR_HASH_SEED` – number of semantic suggestions plus the hash embedding parameters shared by the builder/runtime.
- **Rebuild steps:** rerun the script whenever `Canary_Path_description_maceira.json` or other catalog sources change. The index directory is ignored by Git; keep it in artifact storage if you need to distribute it.

## Metadata-Only Discovery (No Live API)

## Size-Limit Reminder
Every tool and resource response goes through the shared payload guard. If you add a new resource or CLI that surfaces these files, make sure it either:
- keeps responses under `CANARY_MAX_RESPONSE_BYTES`, or
- handles the truncated preview (`{"truncated": true, "preview": "..."}`) gracefully and directs the user to fetch the raw file from disk.

This ensures MCP clients remain deterministic and safe even as we scale the catalog.

## Operational Tooling

- `docs/development/manual-tool-scripts.md` – Command line index for every `scripts/run_*` helper plus the `test_mcp_tools.py` harness. Lists required env variables (CANARY_VIEWS_BASE_URL, CANARY_API_TOKEN, CANARY_SAF_BASE_URL) and sample invocations for faster incident response.
