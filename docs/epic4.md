# EPIC 4 — MCP Server Enhancements, Canary API Contracts, and Workflow Quality

## Goal
Strengthen the MCP server architecture, tools, and LLM workflows for accurate tag discovery, historian read/write, and robust testing. Establish explicit API contracts (READ/WRITE), security boundaries, and measurable acceptance criteria across major sections.

## Brownfield Constraints
- **No changes** to Canary endpoints or server configuration; remain backward-compatible.
- **Response size guardrail:** ≤ **1 MB** per MCP tool invocation; log truncation with `request_id`.
- **Writes restricted to Test datasets only** (e.g., `Test/Maceira`, `Test/Outao`).
- Prefer **on-disk resources** for feasibility.
- **RBAC** (see §6): only the write tool may write to `Test/*` and only roles with a “tester” flag may call it.

Related docs:
- PRD Epic List: `docs/PRD.md` (Epic 4)
- Stories index: `docs/stories/4-all-stories`
- Per-story specs: `docs/stories/4-*.md`
 - API Contracts (local): `docs/aux_files/Canary API` (Views v25.4, SaF v25.3)

---

## 1) Resources & MCP Server
**Objective:** Keep MCP resources current and searchable.

**Tasks**
- Add/update MCP resource:
  - `docs/aux_files/Canary Resources/Canary_Path_description_maceira.json`
  - Wire it into the `maceira_tag_catalog` resource for the tag lookup workflow.
- Keep `canary_time_standards` aligned with Canary docs; ensure unit normalisation rules are present.
- Ensure resource loading is documented (where stored, size limits, refresh cadence).

**Definition of Done (DoD)**
- Resource is deployed, indexed, and visible to MCP.
- Loading is idempotent; failures are logged with actionable errors.

**Acceptance Tests**
- Loading the file yields ≥1 Canary path entries with non-empty descriptions.
- A sample NL query for a known Maceira tag returns the correct Canary path in top-3 candidates.

---

## 2) API Contracts (Explicit)

### 2.1 WRITE (Canary Write API)
**References available in** `docs/aux_files/Canary API` including “Canary Labs Historian Store and Forward Service API Documentation (v25.3)” and Swagger/OpenAPI artefacts.

**Authentication**
- APIs use **tokens** configured in **Identity**; each token maps to a Canary user.
- If **Tag Security** is enabled, the Canary user needs **write** permissions to the target **DataSet(s)** or local Historian view.
- Web API uses `apiToken` parameter (backwards compatibility notes apply per vendor docs).
- If SaF is **remote** from Historian, configure the SaF service with an **API token** as well (can reuse the same token).

**Dataset scope**
- **Use only datasets under `TEST/*`.**
- **Autocreation**: `getSessionToken` supports `autoCreateDatasets=true` → the DataSet is created automatically during session token generation (keep this set in test only).

**DoD**
- MCP write tool enforces `Test/*` only.
- Session/token flow documented with examples; secrets management in place.

**Acceptance Tests**
- Attempt to write outside `Test/*` is blocked with `403` and human-readable error.
- Valid write to `Test/Maceira` succeeds and is verifiable via READ (see §2.2).

---

### 2.2 READ (Canary Views/Read API)
**References available in** `docs/aux_files/Canary API` including “Canary Labs Historian Views Service API Documentation (v25.4)” and Swagger/OpenAPI artefacts.

**Authentication**
- Token-based; each token maps to a Canary user.
- With Tag Security, user must have **read** permissions on the appropriate **View(s)**.
- Web API uses `apiToken`; accepts `accessToken` for backward compatibility if `apiToken` is absent.
- `/getUserToken` remains but credentials must map to an Identity user.

**DoD**
- A typed MCP client for reading historian data with token injection and error typing.
- Pagination/segmenting logic keeps responses ≤1 MB.

**Acceptance Tests**
- Reading a known tag path returns values with correct timestamp order and unit metadata.
- Backwards compatible token path tested (apiToken vs accessToken) if required by environment.

---

## 3) Prompt Workflows (Precision over Guesswork)

### 3.1 `tag_lookup_workflow` (Canonical)
**Pipeline (practical pseudocode)**
- Parse NL → entities (object, measurement, location, asset names) via lightweight NLU or regex + model.
- Normalise tokens (synonyms, units, abbreviations).
- Search metadata index (RAG-like index of tag descriptions & properties) using **embedding similarity + BM25**.
- Pattern match/prefix boost: prioritise tags under `Secil.Portugal` and `site_hint`.
- Rank by combined score (semantic + metadata + prefix).
- If top score ≥ **0.80** → return selected; else return top-N + clarifying question.
- Log query, user, candidate chosen, and confidence.

**DoD**
- Implemented as a single callable workflow; telemetry emitted for every decision branch.

**Acceptance Tests**
- **Input:** 200 NL tag descriptions → **Expectation:** ≥ 90% map to the correct Canary path.
- If confidence < 0.70 → a clarifying question is returned, not a blind pick.
- Malformed input → `400` with a helpful message.

### 3.2 `timeseries_query_workflow`
**DoD**
- NL to API arguments (path, range, aggregate, sampling) is deterministic and validated.

**Acceptance Tests**
- For a fixed tag and time window, the returned series matches Canary’s reference stats (min/max/avg) within tolerance.
- 95th percentile latency target (see §5) is met.

---

## 4) Tools Development & Coverage

### 4.1 Improve Existing Tools
- Enforce result size limits (<1 MB).
- Manual Python test scripts for all tools:
  `ping`, `get_asset_catalog`, `get_tag_metadata`, `get_tag_path`, `get_tag_properties`,
  `list_namespaces`, `get_last_known_values`, `get_server_info`, `get_metrics`,
  `get_metrics_summary`, `get_cache_stats`, `cleanup_expired_cache`, `get_health`.

**DoD**
- All tools return typed, Pythonic results; error paths unit-tested.

**Acceptance Tests**
- Each tool has at least one positive and one negative test.
- Size guardrail verified by a fixture that simulates large responses.

### 4.2 Add/Refactor Tools
- Implement/align with Canary methods:
  `getAggregates`, `getTagProperties`, `getTagData_LastValue`, `getTagData_Aggregate`,
  `getEvents_Limit10`, `browseStatus`, `getAssetTypes`, `getAssetInstances`.

**DoD**
- Each tool ships with an LLM-oriented usage note (when to use, required args, typical failure modes).
- Docs updated in README.

**Acceptance Tests**
- Happy-path call returns expected schema; invalid args return typed errors.

---

## 5) Testing, CI, and Performance

**Local**
- Keep existing `.py` scripts and add harness: `tests/e2e/test_tag_lookup.py`.

**Pre-commit**
- `black` + `isort` + `flake8` + `mypy` (optional).

**CI**
- Separate jobs: unit, integration (NL → Canary tag → data; uses Canary test credentials), and coverage.
- **Fail CI** if **new/changed code coverage drops by >5 pp** vs base.
- **Warn** if repo coverage < 75% (do not block PRs).
- Example:
  ```bash
  uv run pytest --cov=canary_mcp --cov-report=xml
  python scripts/run_integration_tests.py --env test
  ```

**Performance**
- Measure **95th percentile latency** for common calls with **locust** or **k6**.
- Target: **P95 < 300 ms** for tag lookup and metadata reads; **P95 < 600 ms** for typical historian reads (adjust if Canary environment differs).

**Acceptance Tests**
- CI run proves all three jobs pass on a PR with only doc changes (smoke).
- Performance job reports P95 within targets on test env.

---

## 6) Security & Governance

**RBAC**
- Only the **write tool** may write to `Test/*`.
- Only roles with a **“tester”** flag can invoke the write tool.
- All writes are attributed (user/token), logged, and include site/dataset validation.

**DoD**
- Role checks enforced in code; attempted violations recorded with event IDs.

**Acceptance Tests**
- Non-tester role calling write tool → `403`.
- Tester role can write only under `Test/*`.

---

## 7) Documentation & Handover

**README**
- Architecture diagram: NL → (Index) → Canary → LLM.
- Quickstart (env, tokens, running locally).
- How to run unit/integration/perf tests.
- How to add a new resource to the vector index.

**Operational Runbook**
- How to reindex resources.
- How to rotate tokens/keys.
- Incident handling (API failures, quota, auth errors).
- Playbooks for Canary outages and recovery.

**DoD**
- README and Runbook live next to code, referenced from Epic 4 stories.

**Acceptance Tests**
- New engineer can set up and run the e2e test in <30 min following the README.
- On a forced token rotation, system recovers with <10 min operator effort.

---

## 8) Success Criteria (Unchanged, made testable)
1) LLM maps NL tag descriptions to valid Canary API tags, retrieves data, and produces analyses.
2) Plots show correct paths, ranges, units, and site info.
3) LLM asks clarifying questions when metadata is ambiguous.
4) Telemetry confirms ≥ 90% correct top-1 path resolution on the 200-query benchmark.
