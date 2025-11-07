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

## RAG Feasibility (Current vs Future)
- **Current state:** purely local inverted index + curated MCP resources. No external databases, no embeddings, no vector services.
- **Extension path:** Story 4.10 tracks the work to flatten these resources into JSONL, embed them, and drop the vectors into a pluggable index (FAISS/Chroma to start). The MCP server will keep keyword search as the default and treat semantic hits as an additive boost so we never regress on determinism.
- **Operational note:** because resources live in the repo, refreshing the index is as simple as updating the JSON file and restarting the server; once the vector pipeline lands, the same JSON will serve both keyword and semantic flows.

## Size-Limit Reminder
Every tool and resource response goes through the shared payload guard. If you add a new resource or CLI that surfaces these files, make sure it either:
- keeps responses under `CANARY_MAX_RESPONSE_BYTES`, or
- handles the truncated preview (`{"truncated": true, "preview": "..."}`) gracefully and directs the user to fetch the raw file from disk.

This ensures MCP clients remain deterministic and safe even as we scale the catalog.
