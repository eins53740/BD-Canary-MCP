# Story 4.4 — Tools Improvement and Testing

Context & Constraints:
- Apply size caps and consistent error handling across tools.
- Expand coverage with CLI script; keep brownfield endpoints intact.
- Respect API contracts in `docs/aux_files/Canary API` for both READ (Views v25.4) and WRITE (SaF v25.3).
- Write tool must restrict datasets to `Test/*` and may leverage `autoCreateDatasets=true` during session token creation in test environments only.

Acceptance Criteria (Checklist):
- Size-limit guardrail (≤1MB) enforced across listed tools; truncation clearly indicated.
- `scripts/test_mcp_tools.py` exercises core/new tools with human-readable summary.
- Each tool has brief usage guidance for LLMs (“when to use”, params, pitfalls).
- Write tool enforcement: attempts outside `Test/*` are blocked with clear error; valid `Test/*` write succeeds.

Validation:
- Run: `uv run python scripts/test_mcp_tools.py` and confirm PASS summary.
- Review logs for truncation notices and structured errors.

Deliverables:
- Updated CLI validation script and tool docs.
- Consistent error format and size-limit behavior.
