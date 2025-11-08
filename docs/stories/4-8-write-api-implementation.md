# Story 4.8 — Write API Implementation (Test Datasets Only)

Context & Constraints:
- Production is read-only; allow writes strictly to approved test datasets.
- Must confirm dataset/site context before writing.
 - Follow Write API docs in `docs/aux_files/Canary API` (SaF v25.3). Use `apiToken` and ensure Tag Security permissions. If remote SaF, configure it with a valid token.
 - Optionally use `autoCreateDatasets=true` on session token creation for test environments.

Acceptance Criteria (Checklist):
- New write tool records: success/failure (bool) and original prompt (string).
- Writes allowed only to `Test/Maceira` and `Test/Outao`; attempts elsewhere are denied with actionable error.
- Usage documented for LLMs (intent, fields, safeguards).
 - Role-gated: only tester roles can invoke write tool.

Validation:
- Unit/integration tests verify allowed vs denied writes.
- Manual smoke with mock data confirms record shape and gating.

Deliverables:
- Tool spec and docs with safety notes.
- Example usage and clean-up guidance.

---

## Implementation Snapshot (2025-11-07)

- `write_test_dataset` MCP tool added (see `src/canary_mcp/server.py`). It wraps Canary SaF `manualEntryStoreData`, enforces `Test/Maceira` + `Test/Outao` via `validate_test_dataset`, and requires a tester role (`CANARY_TESTER_ROLES`, default `tester`).
- Role gating + dataset whitelist produce structured 403/400 errors and are covered by `tests/unit/test_write_tool.py`.
- SAF session creation now passes `clientId`, `historians`, and `autoCreateDatasets` hints from `.env` (see `CANARY_SAF_AUTO_CREATE_DATASETS` and `CANARY_SAF_FILE_SIZE_MB`).
- Docs updated:
  - README lists the tool, its workflow, and a sample payload with dry-run guidance.
  - `.env.example` documents `CANARY_TESTER_ROLES`, `CANARY_WRITE_ALLOWED_DATASETS`, and the auto-create toggles.
  - `docs/API.md` adds the formal spec, including cleanup instructions.
- Coverage script + unit tests ensure dry-run previews and SAF calls stay deterministic.

**How to validate**
1. Set `CANARY_WRITER_ENABLED=true` and ensure your role is in `CANARY_TESTER_ROLES`.
2. Run `pre-commit run --all-files` (pulls Ruff/Black/isort) and `uv run pytest tests/unit/test_write_tool.py -q`.
3. In MCP Inspector, call `write_test_dataset` with `dry_run=true`. Confirm the `records` preview contains the tag/time/value you expect.
4. Flip `dry_run` to `false` and verify Canary receives the entry (check the SaF dashboard or run `read_timeseries` against the target tag).
5. Clean up the dataset via Canary’s `/deleteRange` endpoint or historian UI if the sample should not persist.
