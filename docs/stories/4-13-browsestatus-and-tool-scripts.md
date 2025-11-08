# Story 4.13 — Browse Status Tool & Manual Script Coverage

**Context**
Epic 4 still lists the Canary `browseStatus` endpoint and a handful of tools lacking dedicated manual scripts. Operators need parity across every MCP tool so they can debug issues without wiring through an MCP client, and browse status is key for validating historian connectivity.

## Objectives
1. **Implement `browse_status` MCP tool**
   - Wrap the Canary `browseStatus` API, respecting the ≤1 MB response guardrail.
   - Inputs: optional `path`, `depth`, `include_tags`. Outputs include `nodes`, `tags`, `next_path`, `cached` metadata, and actionable errors.
   - Follow the existing auth/cache patterns (`search_tags`, `list_namespaces`) and log with `request_id`.
2. **Manual scripts for every MCP tool**
   - Add standalone runners under `scripts/` for the missing tools: `get_events_limit10`, `get_tag_data2`, `invalidate_cache`, `write_test_dataset`, and the new `browse_status`.
   - Each script should accept CLI args/env fallbacks, emit structured logging, and exit non-zero on failure so ops can integrate them into runbooks.
   - Update `scripts/test_mcp_tools.py` (or successor) to reference the new tool + scripts.
3. **Documentation**
   - Extend `README.md` (Tooling section) and `docs/API.md` to describe the `browse_status` tool and link to the full suite of manual scripts.
   - Add a `docs/development/manual-tool-scripts.md` table enumerating every MCP tool → script entry point, expected environment variables, and sample usage.

## Acceptance Criteria
1. `browse_status` tool passes unit + integration tests (happy-path + error handling, pagination if applicable).
2. New scripts live under `scripts/run_<tool>.py`, include `--help`, and are referenced from README + resource index.
3. `scripts/test_mcp_tools.py` (or a new harness) calls the new tool so CI smoke covers it.
4. RBAC + env guardrails (dataset whitelist, tester roles) remain enforced in the `write_test_dataset` script (dry run flag required by default).
5. Documentation clearly states how operators run each script, capture logs, and forward findings in incident tickets.

## Definition of Done
- Code: `browse_status` tool implemented with telemetry + size guard.
- Scripts: Manual runners for all remaining tools committed and linted.
- Tests: Unit coverage for new tool + CLI smoke (use `pytest --cov` to prove lines hit).
- Docs: README/tool references + new script index merged; mention in `docs/resources/resource-index.md` if relevant.

## Extra Scholar Info
Manual scripts double as executable documentation. Giving ops one command per tool reduces ambiguity during outages and makes it trivial to attach evidence when filing tickets against Canary or MCP regressions.
