# Story 4.5 — Definition of Success Validation

Context & Constraints:
- Validate end-to-end outcomes without altering production historians.
- Prefer offline fixtures where live data is unavailable.

Acceptance Criteria (Checklist):
- Test cases demonstrate: multi-tag correlation, accurate retrieval, and summarized insights.
- Ambiguity handling: LLM prompts for clarification; documented example.
- Example plots/text summaries include tag paths, units, sites, and ranges.
- Performance target: p95 latency < 10000 ms for common calls.
- tag_lookup_workflow batch: ≥90% correct mapping across 200 NL descriptions; if confidence <0.7 → ask a clarifying question.

Validation:
- Re-run documented scenarios and verify consistent outputs.
- Keep artifacts small and linkable from docs (not checked-in binaries).

Deliverables:
- Success scenarios documented with steps and expected outputs.
- Lightweight artifacts (images/HTML) referenced from docs as needed.
