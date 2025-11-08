[x] # Story 4.3 — Resource Management and RAG Feasibility

Context & Constraints:
- Use on-disk JSON/CSV resources already shipped; no new infra (DB/vector store).
- Enforce ≤1MB client-facing responses; pre-trim large results.
- Support metadata-only tag discovery (name fragments, descriptions).
- Primary file: `docs/aux_files/Canary Resources/Canary_Path_description_maceira.json` (canonical index).

Acceptance Criteria (Checklist):
- Resource index documented: names, locations, schema, load strategy.
- Metadata-only search path documented and validated on sample data.
- RAG feasibility note added (how resources can augment prompts today; future options).
- Implementation confirms no external vector DB; local index only.

Validation:
- Run: `uv run pytest -q tests/unit/test_search_tags_tool.py`.
- Manual check: search by description/partial names returns bounded results.

Deliverables:
- Resource index doc and RAG feasibility note.
- Size-limiting guidelines referenced from prompt/tool docs.
