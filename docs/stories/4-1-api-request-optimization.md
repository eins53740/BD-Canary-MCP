# Story 4.1 — API Request Optimization

Context & Constraints:
- Brownfield Canary deployment; do not change existing API URLs or server configs.
- Use GET for idempotent lookups; use POST for complex/multi-parameter requests.
- Enforce ≤1MB response payload per MCP tool invocation (truncate + log).
- Align with local API contracts located in `docs/aux_files/Canary API` (Views v25.4 / SaF v25.3).

Acceptance Criteria (Checklist):
- Tool→HTTP method matrix documented and referenced from docs/API.md.
- All tools use the correct HTTP method and return actionable errors on misuse.
- Size guardrail active across tools; truncation logged with request_id.
- Unit tests cover method selection and size-limit behavior for impacted tools.

Definition of Done (Checklist):
- Unit tests passing; integration smoke with Canary test creds.
- Documentation updated with method matrix and examples.

Validation:
- Run: `uv run pytest -q` and `uv run python scripts/test_mcp_tools.py`.
- Spot-check 1–2 tools manually to confirm method and size guardrails.

Deliverables:
- Method usage matrix; updated docs/API.md.
- Changelog entry summarizing refactor and limits.
